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
    dag_id="streaming_monitor_dag",
    default_args=default_args,
    description="DAG 1: Streaming Job Health Monitoring and Auto-restart",
    schedule="*/10 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["streaming", "monitor", "lakehouse"],
) as dag:


    check_streaming_health = BashOperator(
        task_id="check_streaming_health",
        bash_command="""
        PROC_COUNT=$(pgrep -f "FraudDetection_BronzeIngestion" || pgrep -f "FraudDetection_Realtime_Detector" || echo "")
        if [ -z "$PROC_COUNT" ]; then
            echo "Streaming job process not detected! Marking for restart."
            exit 1
        else
            echo "Streaming job is active and healthy (PIDs: $PROC_COUNT)."
            exit 0
        fi
        """,
        trigger_rule="all_success"
    )

    restart_streaming_job = BashOperator(
        task_id="restart_streaming_job",
        bash_command="""
        nohup $SPARK_HOME/bin/spark-submit \
          /home/master/fraud_detection/spark_jobs/streaming/fraud_detector.py \
          > /tmp/streaming_detector.log 2>&1 &
        echo "Streaming detector job successfully restarted."
        """,
        trigger_rule="one_failed"
    )

    check_streaming_health >> restart_streaming_job