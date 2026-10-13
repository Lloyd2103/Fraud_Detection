from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 8, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
    "sla": timedelta(minutes=15),
}

with DAG(
    dag_id="sync_customer_states_dag",
    default_args=default_args,
    description="Batch Lakehouse Sync: Periodic (15-min) Aggregation of Customer Profiles into Silver Delta",
    schedule="*/15 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["lakehouse", "silver", "maintenance", "customer_profile"],
) as dag:

    sync_states_task = BashOperator(
        task_id="sync_customer_states_to_silver",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        export HADOOP_HOME=/home/fraud/hadoop-3.5.0
        export PATH=$HADOOP_HOME/bin:$SPARK_HOME/bin:$PATH
        export PYSPARK_PYTHON=/usr/bin/python3
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3

        $SPARK_HOME/bin/spark-submit \
            --packages io.delta:delta-spark_2.12:3.1.0 \
            --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
            --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
            --master local[2] \
            /home/fraud/fraud_detection/spark_jobs/maintenance/sync_customer_states_to_silver.py
        """,
    )

    sync_states_task
