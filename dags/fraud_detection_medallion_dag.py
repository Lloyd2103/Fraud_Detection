import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 8, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="fraud_detection_medallion_pipeline",
    default_args=default_args,
    description="Automated Medallion Pipeline and ML Retraining",
    schedule="0 * * * *",
    catchup=False,
    max_active_runs=1,
) as dag:

    # Task 1: Bronze to Silver (ĐÃ ĐỔI SANG SPARK STANDALONE)
    bronze_to_silver = BashOperator(
        task_id="transform_bronze_to_silver",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          /home/master/fraud_detection/spark_jobs/transform/bronze_to_silver.py
        """
    )

    # Task 2: Silver to Gold (ĐÃ ĐỔI SANG SPARK STANDALONE)
    silver_to_gold = BashOperator(
        task_id="transform_silver_to_gold",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          /home/master/fraud_detection/spark_jobs/transform/silver_to_gold.py
        """
    )

    # Task 3: Retrain ML Model (ĐÃ ĐỔI SANG SPARK STANDALONE)
    retrain_model = BashOperator(
        task_id="retrain_ml_model",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export PYSPARK_PYTHON=/usr/bin/python3
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --driver-memory 2g \
          --executor-memory 2g \
          --executor-cores 1 \
          --conf spark.pyspark.python=/usr/bin/python3 \
          --conf spark.pyspark.driver.python=/usr/bin/python3 \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          /home/master/fraud_detection/spark_jobs/ml/train_model.py
        """
    )

    bronze_to_silver >> silver_to_gold >> retrain_model
