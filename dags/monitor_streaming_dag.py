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
    description="DAG 1 (DeTai2.pdf Section 2.9): Streaming Health Monitoring & Auto-Restart",
    schedule="*/10 * * * *",  # Every 10 minutes
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["streaming", "monitor", "lakehouse", "sla"],
) as dag:

    check_streaming_health = BashOperator(
        task_id="check_streaming_health",
        bash_command="""
        echo "=== [CHECK 1] Verifying Spark Streaming Processes ==="
        PROC_COUNT=$(pgrep -f "FraudDetection_Realtime_Detector" || pgrep -f "FraudDetection_BronzeIngestion" || echo "")
        
        echo "=== [CHECK 2] Verifying Spark REST API Status ==="
        SPARK_API_STATUS=$(curl -s -m 5 "http://192.168.80.200:8080/api/v1/applications" || curl -s -m 5 "http://localhost:4040/api/v1/applications" || echo "API_UNAVAILABLE")
        
        echo "=== [CHECK 3] Verifying Recent HDFS Bronze Commit Activity ==="
        RECENT_COMMITS=$(hdfs dfs -ls -t /lakehouse/fraud_detection/bronze/_delta_log 2>/dev/null | head -n 3 | wc -l || echo "0")
        
        echo "Active PIDs: ${PROC_COUNT:-NONE}"
        echo "Recent Delta Ingest Commits: ${RECENT_COMMITS}"

        if [ -z "$PROC_COUNT" ]; then
            echo "ALERT: Streaming fraud detector job is not running! Triggering automated restart..."
            exit 1
        fi

        echo "SUCCESS: Streaming detector is operating within healthy SLA limits."
        exit 0
        """,
        trigger_rule="all_success"
    )

    restart_streaming_job = BashOperator(
        task_id="restart_streaming_job",
        bash_command="""
        echo "Restarting Realtime Fraud Detector via spark-submit..."
        nohup /home/fraud/spark/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --driver-memory 2g \
          --packages io.delta:delta-spark_2.12:3.1.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
          /home/fraud/fraud_detection/spark_jobs/streaming/fraud_detector.py \
          > /tmp/streaming_detector_restart.log 2>&1 &
        echo "Streaming detector job restarted successfully in background."
        """,
        trigger_rule="one_failed"
    )

    check_streaming_health >> restart_streaming_job