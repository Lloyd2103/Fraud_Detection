from typing import Any, Dict, Optional

from app.common.helpers import safe_float, safe_int
from app.database.session import SessionLocal
from app.modules.model_governance.repository import model_governance_repository


def _iso(dt) -> Optional[str]:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


class ModelGovernanceService:
    def get_model_performance(self) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            active_model = model_governance_repository.get_active_or_latest_model(db)
            if not active_model:
                return {
                    "available": False,
                    "current_model": None,
                    "models_comparison": [],
                    "drift_monitoring": [],
                    "training_history": [],
                    "feature_importances": [],
                    "message": "No model has been recorded in model_registry yet.",
                }

            is_active = active_model.is_active == 1

            comp_rows = model_governance_repository.get_comparison_models(db, active_model.trained_at)
            models_comparison = []
            if len(comp_rows) > 1:
                for m in comp_rows:
                    state = "ACTIVE" if m.is_active == 1 else "BENCHMARK"
                    models_comparison.append({
                        "algorithm": str(m.algorithm),
                        "model_version": str(m.model_version),
                        "precision_at_200": safe_float(m.precision_at_200),
                        "recall_at_200": safe_float(m.recall_at_200),
                        "pr_auc": safe_float(m.pr_auc),
                        "roc_auc": safe_float(m.roc_auc),
                        "fraud_detected_in_top200": safe_int(m.fraud_detected_in_top200),
                        "promotion_decision": state,
                        "status": state,
                        "trained_at": _iso(m.trained_at),
                    })

            training_history = [
                {
                    "model_version": str(h.model_version),
                    "algorithm": str(h.algorithm),
                    "trained_at": _iso(h.trained_at),
                    "date": h.trained_at.strftime("%d/%m %H:%M") if h.trained_at else str(h.model_version),
                    "precision_at_200": safe_float(h.precision_at_200),
                    "recall_at_200": safe_float(h.recall_at_200),
                    "pr_auc": safe_float(h.pr_auc),
                }
                for h in model_governance_repository.get_training_history(db)
            ]

            drift_monitoring = [
                {
                    "date": str(d.date),
                    "feature_name": str(d.feature_name),
                    "psi": safe_float(d.psi),
                    "ks_statistic": safe_float(d.ks_statistic),
                    "drift_level": str(d.drift_level),
                }
                for d in model_governance_repository.get_all_drift(db)
            ]

            # Values below come only from model_registry. Fields the registry does not store
            # (theoretical maximum, evaluation windows, feature importances, curves) are returned
            # as null/empty instead of being invented.
            tp_top200 = active_model.fraud_detected_in_top200
            return {
                "available": True,
                "current_model": active_model.model_version,
                "algorithm": active_model.algorithm,
                "precision_at_200": safe_float(active_model.precision_at_200),
                "theoretical_max_p200": None,
                "recall_at_200": safe_float(active_model.recall_at_200),
                "pr_auc": safe_float(active_model.pr_auc),
                "roc_auc": safe_float(active_model.roc_auc),
                "fraud_detected_in_top200": safe_int(tp_top200) if tp_top200 is not None else None,
                "total_eval_top200": None,
                "promotion_decision": "ACTIVE" if is_active else "NOT_ACTIVE",
                "status": "ACTIVE" if is_active else "NOT_ACTIVE",
                "features_delta_version": active_model.features_delta_version,
                "trained_at": _iso(active_model.trained_at),
                "models_comparison": models_comparison,
                "training_history": training_history,
                "drift_monitoring": drift_monitoring,
                "feature_importances": [],
                "weekly_precision": [],
                "pr_curve": [],
            }
        finally:
            db.close()

    def list_registry(self) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            rows = model_governance_repository.get_all_registry(db)
            return {
                "status": "success",
                "count": len(rows),
                "models": [
                    {
                        "id": r.id,
                        "model_version": r.model_version,
                        "algorithm": r.algorithm,
                        "gold_delta_version": r.gold_delta_version,
                        "features_delta_version": r.features_delta_version,
                        "model_path": r.model_path,
                        "split_rule": r.split_rule,
                        "eval_rows": r.eval_rows,
                        "source": r.source,
                        "precision_at_200": r.precision_at_200,
                        "pr_auc": r.pr_auc,
                        "roc_auc": r.roc_auc,
                        "f1_score": r.f1_score,
                        "fraud_detected_in_top200": r.fraud_detected_in_top200,
                        "total_test_records": r.total_test_records,
                        "training_data_hash": r.training_data_hash,
                        "notes": r.notes,
                        "is_active": r.is_active,
                        "trained_at": r.trained_at.strftime("%Y-%m-%d %H:%M:%S") if r.trained_at else None,
                    }
                    for r in rows
                ],
            }
        finally:
            db.close()

    def register_model(self, payload_dict: dict) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            record = model_governance_repository.create_registry_entry(db, payload_dict)
            return {
                "status": "success",
                "message": f"Model {record.model_version} registered successfully in model_registry.",
                "id": record.id,
                "model_version": record.model_version,
                "trained_at": _iso(record.trained_at),
            }
        finally:
            db.close()


model_governance_service = ModelGovernanceService()
