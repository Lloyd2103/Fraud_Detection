from datetime import datetime, timedelta
import os
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import BranchPythonOperator
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator

default_args = {
    "owner": "master",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def decide_drift_action():
    status_file = "/tmp/drift_status"
    if not os.path.exists(status_file):
        return "log_stable_status"
        
    with open(status_file, "r") as f:
        status = f.read().strip()
        
    if status == "critical":
        return "trigger_retraining_dag"
    elif status == "warning":
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
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/ml/check_data_drift.py
        """
    )

    branch_operator = BranchPythonOperator(
        task_id="branch_drift_decision",
        python_callable=decide_drift_action,
    )

    log_stable_status = BashOperator(
        task_id="log_stable_status",
        bash_command="echo 'INFO: PSI < 0.1 - Data distribution is STABLE. Logged successfully.'"
    )

    send_email_warning = BashOperator(
        task_id="send_email_warning",
        bash_command="echo 'WARN: 0.1 <= PSI <= 0.25 - Moderate Data Drift detected. Warning alert logged.'"
    )

    trigger_retraining_dag = TriggerDagRunOperator(
        task_id="trigger_retraining_dag",
        trigger_dag_id="model_retraining_dag",
    )

    compute_psi_ks >> branch_operator >> [log_stable_status, send_email_warning, trigger_retraining_dag]