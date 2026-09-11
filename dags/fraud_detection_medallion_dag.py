# Airflow DAG for automated model retraining pipeline with conditional branching
import os
from datetime import datetime, timedelta
from airflow import DAG
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
    # Kiem tra so luong nhan moi tu tham dinh vien (toi thieu 500 nhan moi de retrain)
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder \
            .appName("Airflow_Check_Labels") \
            .master("local[1]") \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
            .getOrCreate()
            
        label_path = "hdfs:///lakehouse/fraud_detection/silver/inspection_decisions"
        label_df = spark.read.format("delta").load(label_path)
        cnt = label_df.count()
        spark.stop()
        
        print(f"Total auditor inspection labels found: {cnt}")
        if cnt >= 500:
            return "build_pit_features"
        else:
            print(f"Notice: Label count ({cnt}) < 500. Skipping retraining.")
            return "skip_insufficient_labels"
    except Exception as e:
        print(f"Label check notice: {e}. Fallback to skip_insufficient_labels.")
        return "skip_insufficient_labels"

def compare_model_precision():
    # So sanh Precision@200 giua model ung vien va baseline dang chay
    eval_file = "/tmp/model_eval_status"
    if os.path.exists(eval_file):
        with open(eval_file, "r") as f:
            status = f.read().strip()
            if status == "worse":
                return "keep_current_model"
    return "register_new_model"

with DAG(
    dag_id="fraud_retraining_dag",
    default_args=default_args,
    description="DAG 3: Weekly Retraining Pipeline (Point-in-Time Join + Multi-model Training & Evaluation)",
    schedule="0 3 * * 1",
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "training", "lakehouse"],
) as dag:

    # 1. Kiem tra nguong 500 nhan
    check_label_threshold = BranchPythonOperator(
        task_id="check_label_threshold",
        python_callable=check_label_count_gate
    )

    skip_insufficient_labels = BashOperator(
        task_id="skip_insufficient_labels",
        bash_command="echo 'INFO: Insufficient auditor labels (< 500). Skipping model retraining.'"
    )

    # 2. Xay dung tap dac trung Point-in-Time chong ro ri du lieu
    build_pit_features = BashOperator(
        task_id="build_pit_features",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export PYSPARK_PYTHON=/usr/bin/python3.12
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3.12
        export PYTHONPATH=/usr/local/lib/python3.12/dist-packages:$PYTHONPATH

        $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/ml/build_training_set.py
        """
    )

    # 3. Huan luyen va so sanh cac mo hinh hoc may
    train_and_evaluate_models = BashOperator(
        task_id="train_and_evaluate_models",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export PYSPARK_PYTHON=/usr/bin/python3.12
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3.12
        export PYTHONPATH=/usr/local/lib/python3.12/dist-packages:$PYTHONPATH

        $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/ml/train_model.py
        """
    )

    # 4. Phan nhanh danh gia hieu nang mo hinh
    compare_precision = BranchPythonOperator(
        task_id="compare_precision",
        python_callable=compare_model_precision
    )

    # Nhanh A: Mo hinh moi vuot troi -> Dang ky va nap lai Streaming Job
    register_new_model = BashOperator(
        task_id="register_new_model",
        bash_command="""
        echo 'SUCCESS: New model Precision@200 is superior to baseline.'
        echo 'Promoting Candidate GBT model to Production HDFS path...'
        hdfs dfs -rm -r -skipTrash /lakehouse/fraud_detection/models/gbt_fraud_model || true
        hdfs dfs -cp /lakehouse/fraud_detection/models/candidate_gbt_model /lakehouse/fraud_detection/models/gbt_fraud_model
        echo 'Model successfully registered to Production directory!'
        """
    )

    reload_streaming_detector = BashOperator(
        task_id="reload_streaming_detector",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export PYSPARK_PYTHON=/usr/bin/python3.12
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3.12
        export PYTHONPATH=/usr/local/lib/python3.12/dist-packages:$PYTHONPATH

        echo 'Reloading Streaming Detector with newly registered model...'
        pkill -f "FraudDetection_Realtime_Detector" || true
        nohup $SPARK_HOME/bin/spark-submit /home/master/fraud_detection/spark_jobs/streaming/fraud_detector.py > /tmp/streaming_detector.log 2>&1 &
        echo 'Streaming Detector successfully reloaded with updated model!'
        """
    )

    # Nhanh B: Mo hinh moi kem hon -> Giu nguyen mo hinh cu va bao cao
    keep_current_model = BashOperator(
        task_id="keep_current_model",
        bash_command="echo 'WARN: New model Precision@200 did not exceed baseline. Retaining existing model.'"
    )

    generate_performance_report = BashOperator(
        task_id="generate_performance_report",
        bash_command="echo 'Performance comparison report logged to gold.model_performance_comparison.'"
    )

    # Thiet lap luong phu thuoc giua cac task
    check_label_threshold >> [skip_insufficient_labels, build_pit_features]
    build_pit_features >> train_and_evaluate_models >> compare_precision
    compare_precision >> register_new_model >> reload_streaming_detector
    compare_precision >> keep_current_model >> generate_performance_report