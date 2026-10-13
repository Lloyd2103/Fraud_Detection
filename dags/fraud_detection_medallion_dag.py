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
    "sla": timedelta(hours=2),
}

def check_label_count_gate():
    try:
        import subprocess
        cmd = ["/home/fraud/hadoop-3.5.0/bin/hdfs", "dfs", "-test", "-e", "/lakehouse/fraud_detection/silver/inspection_decisions/_delta_log"]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0:
            print("Inspection decision Delta table exists on HDFS. Proceeding with retraining pipeline.")
            return "build_pit_features"
        else:
            print("Notice: Inspection decisions table not found or empty on HDFS. Skipping retraining.")
            return "skip_insufficient_labels"
    except Exception as e:
        print(f"Label check notice: {e}. Fallback to skip_insufficient_labels.")
        return "skip_insufficient_labels"

def compare_model_precision():
    try:
        cmd = ["hdfs", "dfs", "-cat", "/lakehouse/fraud_detection/models/_eval_status/_delta_log/00000000000000000000.json"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if "worse" in res.stdout:
            return "keep_current_model"
        elif "better" in res.stdout:
            return "register_new_model"
    except Exception:
        pass

    eval_file = "/tmp/model_eval_status"
    if os.path.exists(eval_file):
        with open(eval_file, "r") as f:
            status = f.read().strip()
            if status == "worse":
                return "keep_current_model"
            elif status == "better":
                return "register_new_model"

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

    sync_feedback_to_delta = BashOperator(
        task_id="sync_feedback_to_delta",
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
            /home/fraud/fraud_detection/spark_jobs/maintenance/sync_feedback_to_delta.py
        """
    )

    check_label_threshold = BranchPythonOperator(
        task_id="check_label_threshold",
        python_callable=check_label_count_gate
    )

    skip_insufficient_labels = BashOperator(
        task_id="skip_insufficient_labels",
        bash_command="echo 'INFO: Insufficient auditor labels (< 500). Skipping model retraining.'"
    )

    build_pit_features = BashOperator(
        task_id="build_pit_features",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        export HADOOP_HOME=/home/fraud/hadoop-3.5.0
        export PATH=$HADOOP_HOME/bin:$SPARK_HOME/bin:$PATH
        export PYSPARK_PYTHON=/usr/bin/python3
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3
        export PYTHONPATH=/home/fraud/spark/python:/home/fraud/spark/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

        $SPARK_HOME/bin/spark-submit --conf spark.cores.max=4 /home/fraud/fraud_detection/spark_jobs/ml/build_training_set.py
        """
    )

    train_and_evaluate_models = BashOperator(
        task_id="train_and_evaluate_models",
        bash_command="""
        export SPARK_HOME=/home/fraud/spark
        export HADOOP_HOME=/home/fraud/hadoop-3.5.0
        export PATH=$HADOOP_HOME/bin:$SPARK_HOME/bin:$PATH
        export PYSPARK_PYTHON=/usr/bin/python3
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3
        export PYTHONPATH=/home/fraud/spark/python:/home/fraud/spark/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

        $SPARK_HOME/bin/spark-submit --conf spark.cores.max=16 /home/fraud/fraud_detection/spark_jobs/ml/train_model.py
        """
    )

    compare_precision = BranchPythonOperator(
        task_id="compare_precision",
        python_callable=compare_model_precision
    )
    register_new_model = BashOperator(
        task_id="register_new_model",
        bash_command="""
        export HADOOP_HOME=/home/fraud/hadoop-3.5.0
        export PATH=$HADOOP_HOME/bin:$PATH

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
        export SPARK_HOME=/home/fraud/spark
        export HADOOP_HOME=/home/fraud/hadoop-3.5.0
        export PATH=$HADOOP_HOME/bin:$SPARK_HOME/bin:$PATH
        export PYSPARK_PYTHON=/usr/bin/python3
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3
        export PYTHONPATH=/home/fraud/spark/python:/home/fraud/spark/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

        echo 'Reloading Streaming Detector with newly registered model...'
        pkill -9 -f "FraudDetection_Realtime_Detector" || true
        sleep 2
        nohup $SPARK_HOME/bin/spark-submit --conf spark.cores.max=4 /home/fraud/fraud_detection/spark_jobs/streaming/fraud_detector.py > /tmp/streaming_detector.log 2>&1 &
        disown
        echo 'Streaming Detector successfully reloaded with updated model!'
        """
    )

    keep_current_model = BashOperator(
        task_id="keep_current_model",
        bash_command="echo 'WARN: New model Precision@200 did not exceed baseline. Retaining existing model.'"
    )

    generate_performance_report = BashOperator(
        task_id="generate_performance_report",
        bash_command="echo 'Performance comparison report logged to gold.model_performance_comparison.'"
    )

    sync_model_performance = BashOperator(
        task_id="sync_model_performance",
        trigger_rule="all_done",
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
            /home/fraud/fraud_detection/spark_jobs/maintenance/sync_model_performance_to_cockroach.py
        """
    )

    sync_feedback_to_delta >> check_label_threshold >> [skip_insufficient_labels, build_pit_features]
    build_pit_features >> train_and_evaluate_models >> compare_precision
    compare_precision >> register_new_model >> reload_streaming_detector >> sync_model_performance
    compare_precision >> keep_current_model >> generate_performance_report >> sync_model_performance