# Endpoints for transaction monitoring, inspection queue, and auditor verdicts
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pyspark.sql.functions import col, lit, count, when
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

@router.get("/alerts", response_model=List[AlertResponse])
def get_pending_alerts(
    status: str = Query("PENDING", alias="status"),
    limit: int = Query(50, ge=1, le=200)
):
    """Retrieve list of pending alerts for auditor inspection from gold.risk_scores."""
    spark = SparkClientManager.get_spark()
    try:
        if not DeltaTable.isDeltaTable(spark, settings.GOLD_RISK_SCORES_PATH):
            return []

        gold_df = spark.read.format("delta").load(settings.GOLD_RISK_SCORES_PATH)
        status_col = "inspection_status" if "inspection_status" in gold_df.columns else ("audit_status" if "audit_status" in gold_df.columns else "inspection_status")

        # Use take(limit) to halt HDFS scan immediately once limit rows are found
        records = gold_df.filter(col(status_col) == status).take(limit)
        response_list = []
        for row in records:
            response_list.append(AlertResponse(
                transaction_id=str(row["transaction_id"]),
                risk_score=float(row["risk_score"]) if "risk_score" in row and row["risk_score"] is not None else 0.0,
                inspection_status=str(row[status_col]) if status_col in row and row[status_col] is not None else "PENDING",
                model_version=str(row["model_version"]) if "model_version" in row and row["model_version"] is not None else "GBT_v1.0",
                latency_ms=int(row["latency_ms"]) if "latency_ms" in row and row["latency_ms"] is not None else 120,
                scored_at=str(row["scored_at"]) if "scored_at" in row and row["scored_at"] is not None else None
            ))
        return response_list
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/alerts/summary")
def get_alerts_summary():
    """Retrieve overview summary of fraud alerts and inspection status counters."""
    spark = SparkClientManager.get_spark()
    try:
        if not DeltaTable.isDeltaTable(spark, settings.GOLD_RISK_SCORES_PATH):
            return {
                "total_alerts": 0,
                "pending": 0,
                "confirmed_fraud": 0,
                "cleared": 0
            }

        gold_df = spark.read.format("delta").load(settings.GOLD_RISK_SCORES_PATH)
        status_col = "inspection_status" if "inspection_status" in gold_df.columns else ("audit_status" if "audit_status" in gold_df.columns else "inspection_status")

        stats = gold_df.groupBy().agg(
            count("transaction_id").alias("total"),
            count(when(col(status_col) == "PENDING", True)).alias("pending"),
            count(when(col(status_col) == "CONFIRMED_FRAUD", True)).alias("confirmed"),
            count(when(col(status_col) == "CLEARED_LEGITIMATE", True)).alias("cleared")
        ).first()

        total_cnt = stats["total"] if stats else 0
        pending_cnt = stats["pending"] if stats else 0
        confirmed_cnt = stats["confirmed"] if stats else 0
        cleared_cnt = stats["cleared"] if stats else 0

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
        status_col = "inspection_status" if "inspection_status" in gold_df.columns else ("audit_status" if "audit_status" in gold_df.columns else "inspection_status")
        
        gold_row = gold_df.filter(col("transaction_id") == id).first()

        if not gold_row:
            raise HTTPException(status_code=404, detail=f"Transaction {id} not found in Gold table")

        # Fetch detailed attributes from Bronze table if available
        bronze_row = None
        if DeltaTable.isDeltaTable(spark, settings.BRONZE_TRANSACTIONS_PATH):
            bronze_df = spark.read.format("delta").load(settings.BRONZE_TRANSACTIONS_PATH)
            bronze_row = bronze_df.filter(col("transaction_id") == id).first()

        risk_factors = []
        if "top_risk_factors" in gold_row and gold_row["top_risk_factors"]:
            for item in gold_row["top_risk_factors"]:
                factor_name = item["feature_name"] if "feature_name" in item else (item["name"] if "name" in item else "Risk Factor")
                risk_factors.append({
                    "name": factor_name,
                    "contribution": float(item["contribution"])
                })

        return TransactionDetailResponse(
            transaction_id=str(gold_row["transaction_id"]),
            risk_score=float(gold_row["risk_score"]) if "risk_score" in gold_row and gold_row["risk_score"] is not None else 0.0,
            inspection_status=str(gold_row[status_col]) if status_col in gold_row and gold_row[status_col] is not None else "PENDING",
            model_version=str(gold_row["model_version"]) if "model_version" in gold_row and gold_row["model_version"] is not None else "GBT_v1.0",
            latency_ms=int(gold_row["latency_ms"]) if "latency_ms" in gold_row and gold_row["latency_ms"] is not None else 120,
            top_risk_factors=risk_factors,
            source_account=str(bronze_row["source_account"]) if bronze_row and "source_account" in bronze_row else (str(gold_row["source_account"]) if "source_account" in gold_row and gold_row["source_account"] is not None else None),
            dest_account=str(bronze_row["dest_account"]) if bronze_row and "dest_account" in bronze_row else (str(gold_row["dest_account"]) if "dest_account" in gold_row and gold_row["dest_account"] is not None else None),
            amount=float(bronze_row["amount"]) if bronze_row and "amount" in bronze_row else (float(gold_row["amount"]) if "amount" in gold_row and gold_row["amount"] is not None else None),
            trans_type=str(bronze_row["trans_type"]) if bronze_row and "trans_type" in bronze_row else (str(gold_row["trans_type"]) if "trans_type" in gold_row and gold_row["trans_type"] is not None else None),
            channel=str(bronze_row["channel"]) if bronze_row and "channel" in bronze_row else (str(gold_row["channel"]) if "channel" in gold_row and gold_row["channel"] is not None else None),
            timestamp=str(bronze_row["timestamp"]) if bronze_row and "timestamp" in bronze_row else (str(gold_row["timestamp"]) if "timestamp" in gold_row and gold_row["timestamp"] is not None else None)
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
        # 1. Append audit decision to Silver Delta table
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

        # 2. Update inspection_status / audit_status in Gold table via Delta MERGE
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

        return VerdictResponse(
            status="SUCCESS",
            transaction_id=id,
            message=f"Verdict registered as {new_status}"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to record verdict: {str(exc)}")