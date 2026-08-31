from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

default_args = {
    "owner": "master",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="retrain_fraud_model",
    default_args=default_args,
    description="Retrain Random Forest Fraud Detection Model",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["batch", "ml", "spark", "delta_lake"],
) as dag:

    retrain_job = BashOperator(
        task_id="run_spark_batch_retrain",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export PYSPARK_PYTHON=/usr/bin/python3
        $SPARK_HOME/bin/spark-submit \
          --master yarn \
          --deploy-mode client \
          --name "Airflow_Model_Retrainer" \
          --driver-memory 1g \
          --executor-memory 1g \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          hdfs://labsoe-17:9000/scripts/batch/train_model.py || true
        """,
    )

    retrain_job
