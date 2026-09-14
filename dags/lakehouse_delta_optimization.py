from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

default_args = {
    "owner": "master",
    "start_date": datetime(2026, 8, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="lakehouse_maintenance_dag",
    default_args=default_args,
    description="DAG 4: Daily Delta Lake OPTIMIZE, Z-ORDER, and VACUUM Maintenance",
    schedule="30 4 * * *",
    catchup=False,
    tags=["maintenance", "delta", "optimization", "lakehouse"],
) as dag:

    optimize_and_vacuum_tables = BashOperator(
        task_id="optimize_and_vacuum_tables",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit --conf spark.cores.max=4 /home/master/fraud_detection/spark_jobs/maintenance/optimize_vacuum.py
        """
    )


    optimize_and_vacuum_tables