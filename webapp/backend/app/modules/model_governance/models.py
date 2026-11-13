from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON
from app.database.base import Base

class ModelPerformance(Base):
    __tablename__ = "model_performance"

    id                       = Column(Integer, primary_key=True, autoincrement=True)
    algorithm                = Column(String(64), nullable=False, unique=True, index=True)
    precision_at_200         = Column(Float, nullable=False, default=0.0)
    pr_auc                   = Column(Float, nullable=False, default=0.0)
    roc_auc                  = Column(Float, nullable=False, default=0.0)
    f1_score                 = Column(Float, nullable=True)
    latency_ms               = Column(Integer, nullable=True)
    fraud_detected_in_top200 = Column(Integer, nullable=True)
    promotion_decision       = Column(String(32), default="better")
    model_role               = Column(String(32), default="candidate")
    weekly_precision         = Column(JSON, nullable=True)
    pr_curve                 = Column(JSON, nullable=True)
    feature_importances      = Column(JSON, nullable=True)
    trained_at               = Column(DateTime, default=datetime.utcnow)

class ModelDrift(Base):
    __tablename__ = "model_drift"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    date         = Column(String(32), nullable=False, index=True)
    feature_name = Column(String(64), nullable=False, index=True)
    psi          = Column(Float, nullable=False, default=0.0)
    ks_statistic = Column(Float, nullable=False, default=0.0)
    drift_level  = Column(String(32), default="stable", index=True)

class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    model_version       = Column(String(64), nullable=False, unique=True, index=True)
    algorithm           = Column(String(64), nullable=False, default="GBTClassifier")
    gold_delta_version  = Column(Integer, nullable=True)
    precision_at_200    = Column(Float, nullable=False, default=0.0)
    pr_auc              = Column(Float, nullable=False, default=0.0)
    roc_auc             = Column(Float, nullable=True)
    f1_score            = Column(Float, nullable=True)
    fraud_detected_in_top200 = Column(Integer, nullable=True)
    total_test_records  = Column(Integer, nullable=True)
    training_data_hash  = Column(String(128), nullable=True)
    notes               = Column(Text, nullable=True)
    trained_at          = Column(DateTime, default=datetime.utcnow)
    model_path          = Column(String(256), nullable=True)
    features_delta_version = Column(Integer, nullable=True)
    split_rule          = Column(String(128), nullable=True)
    eval_rows           = Column(Integer, nullable=True)
    source              = Column(String(64), nullable=True, default="recorded")
    promotion_decision  = Column(String(32), nullable=True)
    is_active           = Column(Integer, nullable=True, default=0)
    recall_at_200       = Column(Float, nullable=True)

