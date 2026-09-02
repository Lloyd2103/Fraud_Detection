import os
from datetime import datetime, timedelta
from airflow import DAG
# Giữ nguyên cấu trúc import chuẩn xác cho hệ thống Airflow 3.0 của bạn
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import BranchPythonOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 8, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

# --- ĐỊNH NGHĨA HÀM RẼ NHÁNH TRƯỚC KHI GỌI ---
def check_data_quality_gate():
    # Chuỗi trả về trùng khớp chính xác với task_id của task đích bên dưới
    return "build_pit_features"


with DAG(
    dag_id="fraud_detection_medallion_pipeline",
    default_args=default_args,
    description="Automated Medallion Pipeline, PIT Feature Store, and GBT Training",
    schedule="0 * * * *", 
    catchup=False,
    max_active_runs=1,
) as dag:

    # Tầng 1: Biến đổi dữ liệu từ Bronze sang Silver
    bronze_to_silver = BashOperator(
        task_id="transform_bronze_to_silver",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export MASTER=spark://labsoe-17:7077
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          /home/master/fraud_detection/spark_jobs/transform/bronze_to_silver.py
        """
    )

    # Tầng 2: Biến đổi dữ liệu từ Silver sang Gold
    silver_to_gold = BashOperator(
        task_id="transform_silver_to_gold",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export MASTER=spark://labsoe-17:7077
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          /home/master/fraud_detection/spark_jobs/transform/silver_to_gold.py
        """
    )

    # Tầng Cổng Kiểm Soát: Nhánh rẽ kiểm tra chất lượng dữ liệu
    quality_check_gate = BranchPythonOperator(
        task_id="data_quality_check_gate",
        python_callable=check_data_quality_gate  # Đã có hàm định nghĩa ở phía trên
    )

    # Nhánh Đạt Đủ Điều Kiện: Tái tạo tập đặc trưng Point-in-Time chống Data Leakage
    build_pit_features = BashOperator(
        task_id="build_pit_features",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export MASTER=spark://labsoe-17:7077
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          /home/master/fraud_detection/spark_jobs/ml/build_training_set.py
        """
    )

    # Nhánh Bị Bỏ Qua: Cảnh báo chất lượng dữ liệu không an toàn
    skip_pipeline_warning = BashOperator(
        task_id="skip_pipeline_warning",
        bash_command="echo 'WARN: Point-in-Time feature generation skipped due to safety gate.'"
    )

    # Tầng Luồng Cuối: Huấn luyện lại mô hình học máy GBT
    train_model = BashOperator(
        task_id="train_ml_model",
        trigger_rule="one_success",  # Chạy ngay khi nhánh build_pit_features thành công
        bash_command="""
        export SPARK_HOME=/home/master/spark
        export MASTER=spark://labsoe-17:7077
        export PYSPARK_PYTHON=/usr/bin/python3
        export PYSPARK_DRIVER_PYTHON=/usr/bin/python3
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --deploy-mode client \
          --driver-memory 2g \
          --executor-memory 2g \
          --executor-cores 1 \
          --conf spark.pyspark.python=/usr/bin/python3 \
          --conf spark.pyspark.driver.python=/usr/bin/python3 \
          --packages io.delta:delta-spark_2.12:3.1.0 \
          /home/master/fraud_detection/spark_jobs/ml/train_model.py
        """
    )

    # === THIẾT LẬP ĐỒ THỊ CHUỖI LIÊN KẾT (WORKFLOW MAP) ===
    
    # 1. Chạy tuần tự qua các tầng dữ liệu Medallion đến điểm kiểm tra dữ liệu
    bronze_to_silver >> silver_to_gold >> quality_check_gate

    # 2. Định nghĩa cấu trúc rẽ 2 nhánh độc lập từ cổng kiểm tra dữ liệu
    quality_check_gate >> build_pit_features
    quality_check_gate >> skip_pipeline_warning

    # 3. Kết nối nhánh xử lý dữ liệu đặc trưng vào bước huấn luyện mô hình cuối cùng
    build_pit_features >> train_model
