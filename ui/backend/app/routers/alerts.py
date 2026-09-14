# Endpoints for transaction monitoring, inspection queue, and auditor verdicts
import time
import math
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pyspark.sql.functions import col, lit
from delta.tables import DeltaTable

from app.core.config import settings
from app.core.spark_session import SparkClientManager
from app.schemas.alert_schema import (
    AlertResponse,
    TransactionDetailResponse,
    VerdictSubmissionRequest,
    VerdictResponse
)

router = APIRouter(prefix="", tags=["Fraud Investigation"])

_alerts_cache = []
_cache_timestamp = 0.0

def safe_int(val, default: int = 120) -> int:
    if val is None:
        return default
    try:
        if isinstance(val, float) and math.isnan(val):
            return default
        return int(float(val))
    except Exception:
        return default

def safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f):
            return default
        return f
    except Exception:
        return default

@router.get("/alerts", response_model=List[AlertResponse])
def get_pending_alerts(
    status: str = Query("PENDING", alias="status"),
    limit: int = Query(50, ge=1, le=200)
):
    """Retrieve list of pending alerts for auditor inspection from gold.risk_scores."""
    global _alerts_cache, _cache_timestamp
    now = time.time()
    
    if (now - _cache_timestamp < 3.0) and _alerts_cache:
        return _alerts_cache[:limit]

    spark = SparkClientManager.get_spark()
    try:
        if not DeltaTable.isDeltaTable(spark, settings.GOLD_RISK_SCORES_PATH):
            return []

        gold_df = spark.read.format("delta").load(settings.GOLD_RISK_SCORES_PATH)
        cols = gold_df.columns
        status_col = "inspection_status" if "inspection_status" in cols else ("audit_status" if "audit_status" in cols else "inspection_status")

        # Column pruning + row slicing: select scalar columns and limit to 2000 candidate rows for sub-second response
        needed_cols = [c for c in ["transaction_id", "ma_giao_dich", "risk_score", status_col, "model_version", "latency_ms", "scored_at", "timestamp"] if c in cols]
        
        pruned_df = gold_df.select(*needed_cols).limit(2000)
        filtered_df = pruned_df.filter(
            (col(status_col) == status) | (col(status_col).isNull()) | (col(status_col) == "PENDING") | (col(status_col) == "new")
        )


        records = filtered_df.limit(limit).toPandas().to_dict(orient="records")

        response_list = []
        for row in records[:limit]:
            tx_id = str(row.get("transaction_id") or row.get("ma_giao_dich") or "TX_UNKNOWN")
            raw_score = safe_float(row.get("risk_score"), 0.0)
            score_pct = raw_score * 100.0 if raw_score <= 1.0 else raw_score

            response_list.append(AlertResponse(
                transaction_id=tx_id,
                risk_score=round(score_pct, 1),
                inspection_status=str(row.get(status_col) or "PENDING"),
                model_version=str(row.get("model_version") or "GBT_v1.0"),
                latency_ms=safe_int(row.get("latency_ms"), 120),
                scored_at=str(row.get("scored_at") or row.get("timestamp") or "")
            ))

        _alerts_cache = response_list
        _cache_timestamp = now
        return response_list
    except Exception as exc:
        print(f"[get_pending_alerts Error] {exc}")
        if _alerts_cache:
            return _alerts_cache[:limit]
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts/summary")
def get_alerts_summary():
    """Retrieve overview summary of fraud alerts and inspection status counters."""
    spark = SparkClientManager.get_spark()
    try:
        if not DeltaTable.isDeltaTable(spark, settings.GOLD_RISK_SCORES_PATH):
            return {"total_alerts": 0, "pending": 0, "confirmed_fraud": 0, "cleared": 0}

        gold_df = spark.read.format("delta").load(settings.GOLD_RISK_SCORES_PATH)
        cols = gold_df.columns
        status_col = "inspection_status" if "inspection_status" in cols else ("audit_status" if "audit_status" in cols else "inspection_status")

        # Fast sample/limit estimation to avoid scanning 3M+ rows
        sample_df = gold_df.limit(5000).toPandas()
        total_cnt = len(sample_df)
        pending_cnt = len(sample_df[sample_df[status_col].isin(["PENDING", "new", None])])
        confirmed_cnt = len(sample_df[sample_df[status_col] == "CONFIRMED_FRAUD"])
        cleared_cnt = len(sample_df[sample_df[status_col] == "CLEARED_LEGITIMATE"])

        return {
            "total_alerts": total_cnt,
            "pending": pending_cnt,
            "confirmed_fraud": confirmed_cnt,
            "cleared": cleared_cnt
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/transactions/{id}", response_model=TransactionDetailResponse)
def get_transaction_detail(id: str):
    """Retrieve full transaction details including top 3 risk factors."""
    spark = SparkClientManager.get_spark()
    try:
        if not DeltaTable.isDeltaTable(spark, settings.GOLD_RISK_SCORES_PATH):
            raise HTTPException(status_code=404, detail="Risk score table not initialized")

        gold_df = spark.read.format("delta").load(settings.GOLD_RISK_SCORES_PATH)
        cols = gold_df.columns
        status_col = "inspection_status" if "inspection_status" in cols else ("audit_status" if "audit_status" in cols else "inspection_status")

        match_df = gold_df.filter(col("transaction_id") == id).limit(1).toPandas()

        if match_df.empty:
            raise HTTPException(status_code=404, detail=f"Transaction {id} not found in Gold table")

        gold_row = match_df.to_dict(orient="records")[0]

        risk_factors = []
        raw_factors = gold_row.get("top_risk_factors")
        if raw_factors:
            if isinstance(raw_factors, str):
                import json
                try:
                    raw_factors = json.loads(raw_factors)
                except Exception:
                    raw_factors = []
            for item in raw_factors:
                if isinstance(item, dict):
                    factor_name = item.get("feature_name") or item.get("name") or "Risk Factor"
                    contrib = safe_float(item.get("contribution") or item.get("weight"), 0.0)
                    risk_factors.append({"name": factor_name, "contribution": contrib})

        raw_score = safe_float(gold_row.get("risk_score"), 0.0)
        score_pct = raw_score * 100.0 if raw_score <= 1.0 else raw_score

        return TransactionDetailResponse(
            transaction_id=str(gold_row.get("transaction_id")),
            risk_score=round(score_pct, 1),
            inspection_status=str(gold_row.get(status_col) or "PENDING"),
            model_version=str(gold_row.get("model_version") or "GBT_v1.0"),
            latency_ms=safe_int(gold_row.get("latency_ms"), 120),
            top_risk_factors=risk_factors,
            source_account=str(gold_row.get("source_account") or "ACC_SOURCE_N/A"),
            dest_account=str(gold_row.get("dest_account") or "ACC_DEST_N/A"),
            amount=safe_float(gold_row.get("amount"), 0.0),
            trans_type=str(gold_row.get("trans_type") or "TRANSFER"),
            channel=str(gold_row.get("channel") or "ONLINE"),
            timestamp=str(gold_row.get("timestamp") or "")
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



@router.post("/transactions/{id}/verdict", response_model=VerdictResponse)
def submit_auditor_verdict(id: str, request: VerdictSubmissionRequest):
    """Write back inspection verdict to Silver inspection_decisions and update Gold inspection_status."""
    spark = SparkClientManager.get_spark()
    try:
        verdict_data = [(
            id,
            request.decision,
            request.auditor,
            datetime.now(),
            request.reason,
            request.handling_time_seconds
        )]
        verdict_columns = [
            "transaction_id", "inspection_label", "auditor_id",
            "inspected_at", "reason", "handling_time_seconds"
        ]
        new_verdict_df = spark.createDataFrame(verdict_data, verdict_columns)
        new_verdict_df.write \
            .format("delta") \
            .mode("append") \
            .option("mergeSchema", "true") \
            .save(settings.SILVER_VERDICTS_PATH)

        new_status = "CONFIRMED_FRAUD" if request.decision == 1 else "CLEARED_LEGITIMATE"
        if DeltaTable.isDeltaTable(spark, settings.GOLD_RISK_SCORES_PATH):
            gold_table = DeltaTable.forPath(spark, settings.GOLD_RISK_SCORES_PATH)
            target_status_col = "inspection_status" if "inspection_status" in gold_table.toDF().columns else "audit_status"
            gold_table.alias("target").merge(
                new_verdict_df.alias("source"),
                "target.transaction_id = source.transaction_id"
            ).whenMatchedUpdate(set={
                target_status_col: lit(new_status)
            }).execute()

        # Invalidate cache so new status is refetched immediately
        global _cache_timestamp
        _cache_timestamp = 0.0

        return VerdictResponse(
            status="SUCCESS",
            transaction_id=id,
            message=f"Verdict registered as {new_status}"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to record verdict: {str(exc)}")