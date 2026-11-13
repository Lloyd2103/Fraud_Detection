from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

class ModelRegistryCreatePayload(BaseModel):
    model_version: str
    precision_at_200: float
    pr_auc: float
    algorithm: Optional[str] = "GBTClassifier"
    gold_delta_version: Optional[int] = None
    features_delta_version: Optional[int] = None
    model_path: Optional[str] = None
    split_rule: Optional[str] = None
    eval_rows: Optional[int] = None
    source: Optional[str] = "spark_train"
    roc_auc: Optional[float] = None
    notes: Optional[str] = None
    recall_at_200: Optional[float] = None
    fraud_detected_in_top200: Optional[int] = None
    promotion_decision: Optional[str] = None
    is_active: Optional[int] = None
    trained_at: Optional[datetime] = None

class ModelRegistryOut(BaseModel):
    id: int
    model_version: str
    algorithm: str
    precision_at_200: float
    pr_auc: float
    roc_auc: Optional[float] = None
    gold_delta_version: Optional[int] = None
    features_delta_version: Optional[int] = None
    model_path: Optional[str] = None
    trained_at: Optional[str] = None
    is_active: Optional[int] = 0

class ModelPerformanceOut(BaseModel):
    models: List[Any]
    feature_drift: List[Any]
    last_evaluated_at: Optional[str] = None

