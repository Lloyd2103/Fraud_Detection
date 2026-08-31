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
    dag_id="check_data_drift",
    default_args=default_args,
    description="Check data and model drift on fraud transactions",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["drift", "mlops", "quality"],
) as dag:

    verify_bronze_layer = BashOperator(
        task_id="check_bronze_transactions_count",
        bash_command="""
        hdfs dfs -count -q -h -v /lakehouse/fraud_detection || true
        """,
    )

    verify_bronze_layer
