import concurrent.futures
import glob
import hashlib
import json
import os
import re
import threading
from typing import Any, Dict, List, Optional

from deltalake import DeltaTable

from app.common.cache import TTLCache
from app.common.constants import CACHE_TTL_TIME_TRAVEL
from app.common.helpers import clean_for_json, safe_float, safe_int
from app.config.settings import settings
from app.core.exceptions import (
    AppException,
    BadRequestError,
    ConflictError,
    GatewayTimeoutError,
    NotFoundError,
    PermissionDeniedError,
    ServiceUnavailableError,
    TooManyRequestsError,
)
from app.database.session import SessionLocal
from app.integrations.delta_lake import TABLE_CONFIGS
from app.modules.model_governance.models import ModelRegistry
from app.modules.verdicts.service import verdict_service

_NOT_FOUND_MARKERS = ("logsegment end version", "not the same as the specified end version", "cannot find version", "file not found")
# (substring in the lower-cased error text, short reason shown to the user), most specific first.
_HDFS_REASONS = (
    ("connection refused", "connection refused"),
    ("connection reset", "connection reset"),
    ("timed out", "timed out"),
    ("no route to host", "no route to host"),
    ("unable to load libhdfs", "HDFS client library not loaded"),
    ("failed to connect", "failed to connect"),
    ("namenode", None),
    ("hdfs", None),
)
_MATCH_TOLERANCE = 0.0001
_ANSI_RE = re.compile(r"(?:\x1b)?\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    """Remove terminal colour codes (\x1b[31m, [0m, ...) that delta-rs/Rust errors can carry."""
    return _ANSI_RE.sub("", text or "")


def _hdfs_down_reason(exc: Exception, msg_lower: str) -> Optional[str]:
    """Return a short reason when the error means HDFS cannot be reached, '' when the reason is unknown, else None."""
    for marker, reason in _HDFS_REASONS:
        if marker in msg_lower:
            return reason or ""
    if isinstance(exc, ConnectionError):
        return "connection refused"
    if isinstance(exc, TimeoutError):
        return "timed out"
    return None


def _raise_for_delta_error(exc: Exception, version: Optional[int] = None) -> None:
    """Translate a delta-rs/HDFS failure into an HTTP-mapped AppException with a short, clean message."""
    msg = _strip_ansi(str(exc))
    low = msg.lower()
    if any(m in low for m in _NOT_FOUND_MARKERS):
        what = f"Delta version {version}" if version is not None else "The requested Delta version"
        raise NotFoundError({"error": "NOT_FOUND", "message": f"{what} does not exist in the commit log."})
    reason = _hdfs_down_reason(exc, low)
    if reason is not None:
        raise ServiceUnavailableError(f"HDFS is unreachable ({reason})" if reason else "HDFS is unreachable")
    short = " ".join(msg.split())[:300]
    raise AppException(status_code=500, detail=f"Delta Lake query failed: {short}")


class TimeTravelService:
    def __init__(self):
        self._semaphore = threading.BoundedSemaphore(1)
        self._cache = TTLCache(default_ttl_seconds=CACHE_TTL_TIME_TRAVEL)
        self._rerun_lock = threading.Lock()
        self._rerun_active: bool = False

    # ------------------------------------------------------------------ time travel
    def get_time_travel_audit(self, delta_version: int = 0, table_name: str = "gold/risk_scores") -> Dict[str, Any]:
        norm_table = (table_name or "gold/risk_scores").strip().replace(".", "/")
        if norm_table not in TABLE_CONFIGS:
            raise BadRequestError(f"Invalid table '{table_name}'. Supported: {', '.join(TABLE_CONFIGS.keys())}")

        cache_key = (norm_table, delta_version)
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        if not self._semaphore.acquire(blocking=False):
            raise TooManyRequestsError("Another Time Travel query is already running. Please retry in a moment.")

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._read_snapshot_raw, delta_version, norm_table)
            result = future.result(timeout=30)
            self._cache.set(cache_key, result)
            return result
        except concurrent.futures.TimeoutError:
            raise GatewayTimeoutError(f"Time Travel query for version {delta_version} exceeded the 30 s limit.")
        except AppException:
            raise
        except Exception as e:
            _raise_for_delta_error(e, delta_version)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            self._semaphore.release()

    def _read_snapshot_raw(self, delta_version: int, norm_table: str) -> Dict[str, Any]:
        meta = TABLE_CONFIGS[norm_table]
        target_path = meta["hdfs_path"]

        dt = DeltaTable(target_path, version=delta_version)
        total_records = dt.count()

        sample_rows: List[Dict[str, Any]] = []
        batches = dt.to_pyarrow_dataset().scanner(batch_size=50).to_batches()
        first_batch = next(batches, None)
        if first_batch is not None:
            sample_rows = first_batch.slice(0, 50).to_pylist()

        file_uris = sorted(dt.file_uris())
        hasher = hashlib.sha256()
        hasher.update(f"{norm_table}:{delta_version}:{total_records}:{len(file_uris)}".encode("utf-8"))
        for uri in file_uris:
            hasher.update(uri.encode("utf-8"))

        head_ver = DeltaTable(target_path).version()
        commit_history = clean_for_json(DeltaTable(target_path).history(limit=145))

        return {
            "status": "success",
            "version": delta_version,
            "requested_version": delta_version,
            "target_table": norm_table,
            "target_path": target_path,
            "total_records": total_records,
            "commit_history": commit_history,
            "sample_data": clean_for_json(sample_rows),
            "hashed_columns": [meta["id_col"], meta["val_col"]],
            # True only when the requested version exists in the log and was readable (this code path).
            "audit_compliance_verified": 0 <= delta_version <= head_ver,
            "reproducible_hash": f"SHA256:{hasher.hexdigest()}",
            "head_version": head_ver,
            "files_count": len(file_uris),
        }

    def get_delta_commits(self, limit: int = 145, table_name: str = "gold/risk_scores") -> List[Dict[str, Any]]:
        clean_name = (table_name or "gold/risk_scores").strip().replace(".", "/")
        if clean_name not in TABLE_CONFIGS:
            raise BadRequestError(f"Invalid table '{table_name}'. Supported: {', '.join(TABLE_CONFIGS.keys())}")
        try:
            return clean_for_json(DeltaTable(TABLE_CONFIGS[clean_name]["hdfs_path"]).history(limit=limit))
        except Exception as e:
            _raise_for_delta_error(e)

    def get_audit_trail(self, limit: int = 50) -> List[Dict[str, Any]]:
        return verdict_service.get_inspected_alerts(limit=limit).get("data", [])

    def audit_by_version(self, version: str, table: Optional[str] = None) -> Dict[str, Any]:
        clean_key = version.strip()
        delta_ver = None
        target_tbl = table

        with SessionLocal() as db:
            reg = db.query(ModelRegistry).filter(
                (ModelRegistry.model_version == clean_key) | (ModelRegistry.model_version.ilike(f"%{clean_key}%"))
            ).order_by(ModelRegistry.trained_at.desc()).first()
            if reg:
                if reg.features_delta_version is not None:
                    delta_ver = reg.features_delta_version
                    target_tbl = target_tbl or "features"
                elif reg.gold_delta_version is not None:
                    delta_ver = reg.gold_delta_version
                    target_tbl = target_tbl or "gold/risk_scores"

        if delta_ver is None:
            try:
                delta_ver = int(clean_key)
            except ValueError:
                raise NotFoundError(f"Model version '{version}' was not found in model_registry")

        return self.get_time_travel_audit(delta_version=delta_ver, table_name=target_tbl or "features")

    # ------------------------------------------------------------------ rerun evaluation
    def rerun_evaluation(self, delta_version: int = 0, table_name: str = "gold/risk_scores",
                         force_recompute: bool = False, is_admin: bool = False) -> Dict[str, Any]:
        if force_recompute and not is_admin:
            raise PermissionDeniedError("Only administrators may force a recomputation that bypasses saved results.")

        with self._rerun_lock:
            if self._rerun_active:
                raise ConflictError("An evaluation re-run is already in progress. Please wait.")
            self._rerun_active = True
        try:
            return self._execute_rerun(delta_version, table_name, force_recompute)
        finally:
            with self._rerun_lock:
                self._rerun_active = False

    @staticmethod
    def _eval_results_dir() -> str:
        return settings.EVAL_RESULTS_DIR or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "eval_results")

    @staticmethod
    def _unavailable(delta_version: int, table_name: str, reason: str) -> Dict[str, Any]:
        return {"status": "UNAVAILABLE", "available": False, "delta_version": delta_version,
                "table_name": table_name, "reason": reason, "message": reason}

    def _execute_rerun(self, delta_version: int, table_name: str, force_recompute: bool) -> Dict[str, Any]:
        tbl_clean = (table_name or "").lower()
        if "feature" in tbl_clean:
            link_col = ModelRegistry.features_delta_version
        elif "gold" in tbl_clean or "risk" in tbl_clean:
            link_col = ModelRegistry.gold_delta_version
        else:
            return self._unavailable(delta_version, table_name,
                                     f"Table '{table_name}' is not linked to model_registry (only features and gold are tracked).")

        with SessionLocal() as db:
            reg = None
            if delta_version > 0:
                reg = db.query(ModelRegistry).filter(
                    link_col == delta_version, ModelRegistry.model_path.isnot(None)
                ).order_by(ModelRegistry.trained_at.desc()).first()
            if not reg:
                reg = db.query(ModelRegistry).filter(
                    ModelRegistry.model_path.isnot(None)
                ).order_by(ModelRegistry.trained_at.desc()).first()
            if not reg:
                return self._unavailable(delta_version, table_name,
                                         f"No MLlib model in model_registry is linked to version {delta_version} of '{table_name}'.")

            model_ver = reg.model_version
            expected = {
                "p200": safe_float(reg.precision_at_200),
                "recall": safe_float(reg.recall_at_200),
                "prauc": safe_float(reg.pr_auc),
                "tp": safe_int(reg.fraud_detected_in_top200, default=-1),
            }
            features_ver = reg.features_delta_version

        if force_recompute:
            return self._unavailable(delta_version, table_name,
                                     "Recomputation from the Delta snapshot is not available in the web API yet. "
                                     "Run the evaluation job and save its JSON result in the evaluation-results folder.")

        saved = self._load_saved_evaluation(model_ver)
        if saved is None:
            return self._unavailable(delta_version, table_name,
                                     f"No saved evaluation result was found for model {model_ver}. "
                                     "Nothing was recomputed, so no reproducibility claim can be made.")

        data, file_name = saved
        rep_p200 = data.get("reproduced_precision_at_200", data.get("precision_at_200"))
        rep_recall = data.get("reproduced_recall_at_200", data.get("recall_at_200"))
        rep_prauc = data.get("reproduced_pr_auc", data.get("pr_auc"))
        rep_tp = data.get("tp_count")
        eval_rows = data.get("eval_rows")

        def _status(reproduced: Any, original: float) -> str:
            if reproduced is None:
                return "NOT_AVAILABLE"
            return "MATCH" if abs(float(reproduced) - original) < _MATCH_TOLERANCE else "MISMATCH"

        p200_status = _status(rep_p200, expected["p200"])
        recall_status = _status(rep_recall, expected["recall"])
        tp_status = "NOT_AVAILABLE" if (rep_tp is None or expected["tp"] < 0) else ("MATCH" if int(rep_tp) == expected["tp"] else "MISMATCH")

        return {
            "status": "COMPLETED",
            "source_type": "saved",
            "source_label": "Saved evaluation result (not recomputed)",
            "message": f"Comparison of the registry values with the saved evaluation file '{file_name}'. No recomputation was performed.",
            "model_version": model_ver,
            "delta_version": delta_version,
            "gold_delta_version": delta_version,
            "features_delta_version": features_ver,
            "original_precision_at_200": expected["p200"], "reproduced_precision_at_200": safe_float(rep_p200) if rep_p200 is not None else None,
            "p200_status": p200_status,
            "original_recall_at_200": expected["recall"], "reproduced_recall_at_200": safe_float(rep_recall) if rep_recall is not None else None,
            "recall_status": recall_status,
            "original_pr_auc": expected["prauc"], "reproduced_pr_auc": safe_float(rep_prauc) if rep_prauc is not None else None,
            "original_tp": expected["tp"] if expected["tp"] >= 0 else None,
            "reproduced_tp": safe_int(rep_tp) if rep_tp is not None else None,
            "tp_status": tp_status,
            "reproducible_match": "MISMATCH" not in (p200_status, recall_status, tp_status) and "MATCH" in (p200_status, recall_status, tp_status),
            "eval_rows": eval_rows,
            "records_evaluated": eval_rows,
            "eval_file": file_name,
        }

    def _load_saved_evaluation(self, model_ver: str):
        eval_dir = os.path.abspath(self._eval_results_dir())
        if not os.path.isdir(eval_dir):
            return None
        candidates = glob.glob(os.path.join(eval_dir, f"*{model_ver}*.json"))
        for path in sorted(candidates, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                continue
            if data.get("status") in ("SUCCESS", "COMPLETED") or "reproduced_precision_at_200" in data:
                return data, os.path.basename(path)
        return None


time_travel_service = TimeTravelService()
