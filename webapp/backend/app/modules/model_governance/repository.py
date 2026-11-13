from typing import List, Optional
from datetime import timedelta
from sqlalchemy.orm import Session
from app.modules.model_governance.models import ModelRegistry, ModelDrift

class ModelGovernanceRepository:
    def get_active_or_latest_model(self, db: Session) -> Optional[ModelRegistry]:
        active = db.query(ModelRegistry).filter(ModelRegistry.is_active == 1).first()
        if not active:
            active = db.query(ModelRegistry).order_by(ModelRegistry.trained_at.desc()).first()
        return active

    def get_comparison_models(self, db: Session, trained_at) -> List[ModelRegistry]:
        if not trained_at:
            return []
        window_start = trained_at - timedelta(minutes=10)
        window_end = trained_at + timedelta(minutes=10)
        return db.query(ModelRegistry).filter(
            ModelRegistry.trained_at.between(window_start, window_end)
        ).order_by(ModelRegistry.precision_at_200.desc()).all()

    def get_training_history(self, db: Session) -> List[ModelRegistry]:
        return db.query(ModelRegistry).filter(
            ModelRegistry.source == "recorded"
        ).order_by(ModelRegistry.trained_at.asc()).all()

    def get_all_drift(self, db: Session) -> List[ModelDrift]:
        return db.query(ModelDrift).order_by(ModelDrift.psi.desc()).all()

    def get_all_registry(self, db: Session) -> List[ModelRegistry]:
        return db.query(ModelRegistry).order_by(ModelRegistry.trained_at.desc()).all()

    def get_registry_by_version(self, db: Session, model_version: str) -> Optional[ModelRegistry]:
        return db.query(ModelRegistry).filter(ModelRegistry.model_version == model_version).first()

    def create_registry_entry(self, db: Session, payload_dict: dict) -> ModelRegistry:
        existing = self.get_registry_by_version(db, payload_dict["model_version"])
        if existing:
            for k, v in payload_dict.items():
                if v is not None:
                    setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            entry = ModelRegistry(**payload_dict)
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry

model_governance_repository = ModelGovernanceRepository()
