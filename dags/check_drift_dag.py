from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

default_args = {
    "owner": "master",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

STATUS_PATH_HDFS = "/lakehouse/fraud_detection/models/_drift_status"


def _read_drift_status():
    """
    Đọc status từ Delta table trên HDFS.
    Thử deltalake trước; nếu fail, fallback về đọc _delta_log / parquet trực tiếp.
    """
    # Cách 1: deltalake (cần cấu hình HDFS core-site nếu dùng hdfs://)
    try:
        from deltalake import DeltaTable
        dt = DeltaTable(f"hdfs://{STATUS_PATH_HDFS.lstrip('/')}")
        df = dt.to_pandas()
        return str(df["status"].iloc[0])
    except Exception as e:
        print(f"[deltalake] không đọc được: {e}")

    # Cách 2: dùng pyarrow đọc parquet trong thư mục Delta
    try:
        import subprocess
        import pyarrow.parquet as pq

        result = subprocess.run(
            ["hdfs", "dfs", "-ls", STATUS_PATH_HDFS],
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 8 and parts[-1].endswith(".parquet"):
                local_tmp = "/tmp/drift_status.parquet"
                subprocess.run(
                    ["hdfs", "dfs", "-get", parts[-1], local_tmp],
                    check=True, timeout=15
                )
                table = pq.read_table(local_tmp)
                return str(table.column("status")[0].as_py())
    except Exception as e:
        print(f"[hdfs fallback] không đọc được: {e}")

    return None


def decide_drift_action():
    status = _read_drift_status()
    print(f"Drift status đọc được: {status}")

    if status == "critical":
        return "trigger_retraining_dag"
    elif status in ("warning", "error"):
        return "send_email_warning"
    else:
        return "log_stable_status"


with DAG(
    dag_id="data_drift_monitor_dag",
    default_args=default_args,
    description="DAG 2: Daily PSI & KS Statistic Data Drift Monitoring",
    schedule="0 1 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["drift", "mlops", "quality", "lakehouse"],
) as dag:

    compute_psi_ks = BashOperator(
        task_id="compute_psi_ks",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        $SPARK_HOME/bin/spark-submit \
            --packages io.delta:delta-spark_2.12:3.1.0 \
            --conf spark.cores.max=4 \
            --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
            --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
            /home/fraud/fraud_detection/spark_jobs/ml/check_data_drift.py
        """,
        retries=2,
    )

    branch_operator = BranchPythonOperator(
        task_id="branch_drift_decision",
        python_callable=decide_drift_action,
    )

    log_stable_status = BashOperator(
        task_id="log_stable_status",
        bash_command=(
            "echo 'INFO: PSI < 0.1 - Data distribution is STABLE. Logged successfully.'"
        ),
    )

    send_email_warning = BashOperator(
        task_id="send_email_warning",
        bash_command=(
            "echo 'WARN: PSI >= 0.1 - Data drift detected (warning hoặc error). "
            "Warning alert logged.'"
        ),
    )

    trigger_retraining_dag = TriggerDagRunOperator(
        task_id="trigger_retraining_dag",
        trigger_dag_id="fraud_retraining_dag",
    )

    compute_psi_ks >> branch_operator >> [
        log_stable_status,
        send_email_warning,
        trigger_retraining_dag,
    ]