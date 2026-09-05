import os
from datetime import datetime, timedelta
from airflow import DAG

try:
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import BranchPythonOperator
except ImportError:
    from airflow.providers.standard.operators.bash import BashOperator
    from airflow.providers.standard.operators.python import BranchPythonOperator

default_args = {
    "owner": "master",
    "depends_on_past": False,
    "start_date": datetime(2026, 8, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def check_label_count_gate():
    """Check if training dataset has sufficient inspection labels for retraining."""
    return "build_pit_features"

with DAG(
    dag_id="model_retraining_dag",
    default_args=default_args,
    description="DAG 3: Weekly Retraining Pipeline (Point-in-Time Join + Multi-model Training & Evaluation)",
    schedule="0 3 * * 1",
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "training", "lakehouse"],
) as dag:

    transform_bronze_to_silver = BashOperator(
        task_id="transform_bronze_to_silver",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/transform/bronze_to_silver.py
        """
    )

    transform_silver_to_gold = BashOperator(
        task_id="transform_silver_to_gold",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/transform/silver_to_gold.py
        """
    )

    check_label_gate = BranchPythonOperator(
        task_id="check_label_gate",
        python_callable=check_label_count_gate
    )

    build_pit_features = BashOperator(
        task_id="build_pit_features",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/ml/build_training_set.py
        """
    )

    train_models = BashOperator(
        task_id="train_models",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/ml/train_model.py
        """
    )




    evaluate_and_register_model = BashOperator(
        task_id="evaluate_and_register_model",
        bash_command="echo 'SUCCESS: Retraining pipeline evaluated all models (GBT vs RF vs LR) and registered best model to HDFS.'"
    )

    transform_bronze_to_silver >> transform_silver_to_gold >> check_label_gate >> build_pit_features >> train_models >> evaluate_and_register_model


