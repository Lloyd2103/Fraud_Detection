from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "ml_engineer",
    "start_date": datetime(2026, 8, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "sla": timedelta(hours=1), # ML job nặng nên cấp hạn SLA 1 tiếng
}

with DAG(
    dag_id="fraud_detection_ml_retraining",
    default_args=default_args,
    description="Heavy Weekly ML Point-in-Time Feature Extraction and Retraining",
    schedule="0 0 * * 0", # Chạy vào 00:00 mỗi Chủ Nhật hàng tuần
    catchup=False,
    max_active_runs=1,
) as dag:

        check_drift = BashOperator(
        task_id="check_data_drift_status",
        # Cho phép Airflow chấp nhận mã exit code 10 là trạng thái thành công cần chuyển nhánh
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          /home/master/fraud_detection/spark_jobs/ml/check_data_drift.py
        """
    )


    # Gọi file trích xuất đặc trưng Point-in-Time vừa viết để chống Data Leakage
    build_features = BashOperator(
        task_id="build_pit_features",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export MASTER=spark://labsoe-17:7077
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          /home/master/fraud_detection/spark_jobs/ml/build_training_set.py
        """
    )

    # Tiến hành train model từ nguồn features/ sạch
    train_model = BashOperator(
        task_id="train_random_forest_model",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export MASTER=spark://labsoe-17:7077
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --driver-memory 2g \
          --executor-memory 2g \
          /home/master/fraud_detection/spark_jobs/ml/train_model.py
        """
    )

    check_drift >> build_features >> train_model
