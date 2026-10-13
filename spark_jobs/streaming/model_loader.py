# Model loader singleton for Spark Driver and Workers
import os
from dotenv import load_dotenv
from pyspark.ml import PipelineModel

for env_p in ["/home/fraud/fraud_detection/.env", ".env"]:
    if os.path.exists(env_p):
        load_dotenv(env_p)
        break

_model = None

def get_model(prod_path=None, candidate_path=None):
    """Load model instance once as a singleton."""
    global _model
    if prod_path is None:
        prod_path = os.getenv("MODEL_PATH", "hdfs:///lakehouse/fraud_detection/models/gbt_fraud_model")
    if candidate_path is None:
        candidate_path = os.getenv("CANDIDATE_PATH", "hdfs:///lakehouse/fraud_detection/models/candidate_gbt_model")

    if _model is None:
        try:
            print(f"[ModelLoader] Loading model from {prod_path}...", flush=True)
            _model = PipelineModel.load(prod_path)
            print(f"[ModelLoader] Successfully loaded production model from {prod_path}", flush=True)
        except Exception as e:
            print(f"[ModelLoader] Production model unavailable ({e}), falling back to candidate: {candidate_path}", flush=True)
            _model = PipelineModel.load(candidate_path)
            print(f"[ModelLoader] Successfully loaded candidate model from {candidate_path}", flush=True)
    return _model
