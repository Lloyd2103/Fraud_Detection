from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import BranchPythonOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 8, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="training_model",
    default_args=default_args,
    description="Training Model, PIT Features",
    schedule="0 3 * * 1",  # Weekly run at 03:00 Monday
    catchup=False,
    max_active_runs=1,
    tags=["training", "mlops", "point-in-time", "gbt"],
) as dag:

    # 1. Medallion Ingestion: Bronze to Silver
    bronze_to_silver = BashOperator(
        task_id="transform_bronze_to_silver",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        $SPARK_HOME/bin/spark-submit \
          /home/fraud/fraud_detection/spark_jobs/transform/bronze_to_silver.py --full
        """
    )

    # 2. Medallion Aggregations: Silver to Gold
    silver_to_gold = BashOperator(
        task_id="transform_silver_to_gold",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        $SPARK_HOME/bin/spark-submit \
          /home/fraud/fraud_detection/spark_jobs/transform/silver_to_gold.py
        """
    )

    # 4. Point-in-Time Feature Store (No Data Leakage)
    build_pit_features = BashOperator(
        task_id="build_pit_features",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        $SPARK_HOME/bin/spark-submit \
          /home/fraud/fraud_detection/spark_jobs/ml/build_training_set.py
        """
    )

    # 6. Multi-Model Training & Precision@200 Evaluation
    train_model = BashOperator(
        task_id="train_ml_model",
        trigger_rule="one_success",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        $SPARK_HOME/bin/spark-submit \
          /home/fraud/fraud_detection/spark_jobs/ml/train_model.py
        """
    )

    # === WORKFLOW DEPENDENCY MAP ===
    bronze_to_silver >> silver_to_gold >> build_pit_features >> train_model 
    