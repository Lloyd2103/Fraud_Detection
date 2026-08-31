from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

default_args = {
    "owner": "master",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="monitor_streaming_job",
    default_args=default_args,
    description="Check health of Streaming Fraud Detector on YARN",
    schedule="*/10 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["streaming", "yarn", "monitor"],
) as dag:

    check_yarn_app = BashOperator(
        task_id="check_yarn_streaming_app",
        bash_command="""
        APP_COUNT=$(yarn application -list | grep -c "Streaming_Fraud_Detector")
        if [ "$APP_COUNT" -eq 0 ]; then
            echo "Streaming Job is not running! Triggering alert..."
            exit 1
        else
            echo "Streaming Job is healthy and RUNNING."
        fi
        """,
    )

    check_yarn_app
