from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import BranchPythonOperator
from deltalake import DeltaTable

default_args = {
    "owner": "master",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

STATUS_PATH = "hdfs:///lakehouse/fraud_detection/models/_eval_status"


def check_eval_status():
    try:
        dt = DeltaTable(STATUS_PATH)
        df = dt.to_pandas()
        decision = df["decision"].iloc[0]
    except Exception:
        return "keep_current_model"

    return "promote_model" if decision == "better" else "keep_current_model"


with DAG(
    dag_id="model_retraining_dag",
    default_args=default_args,
    description="Weekly retraining with point-in-time join",
    schedule="0 3 * * 0",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["ml", "training", "lakehouse"],
) as dag:

    build_training_set = BashOperator(
        task_id="build_training_set",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit \
            --packages io.delta:delta-spark_2.12:3.1.0 \
            --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
            --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
            /home/master/fraud_detection/spark_jobs/ml/build_training_set.py
        """,
    )

    train_model = BashOperator(
        task_id="train_model",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit \
            --packages io.delta:delta-spark_2.12:3.1.0 \
            --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
            --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
            /home/master/fraud_detection/spark_jobs/ml/train_model.py
        """,
    )

    branch = BranchPythonOperator(
        task_id="branch_model_promotion",
        python_callable=check_eval_status,
    )

    promote_model = BashOperator(
        task_id="promote_model",
        bash_command="echo 'Model promoted to production.'",
    )

    keep_current = BashOperator(
        task_id="keep_current_model",
        bash_command="echo 'Keeping current model.'",
    )

    build_training_set >> train_model >> branch >> [promote_model, keep_current]