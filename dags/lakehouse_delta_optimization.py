from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "devops_data",
    "start_date": datetime(2026, 8, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="lakehouse_delta_optimization",
    default_args=default_args,
    description="Daily Delta Lake Optimize and Vacuum Maintenance",
    schedule="0 0 * * *", # Chạy vào lúc 12h đêm mỗi ngày
    catchup=False,
) as dag:

    # Kích hoạt dọn dẹp và tối ưu hóa file Parquet nhỏ trên HDFS để NameNode nhẹ máy
    optimize_bronze = BashOperator(
        task_id="optimize_delta_tables",
        bash_command="""
        export SPARK_HOME=/home/master/spark
        $SPARK_HOME/bin/spark-submit \
          --master spark://labsoe-17:7077 \
          --execute "
          spark.read.format('delta').load('hdfs://labsoe-17:9000/lakehouse/fraud_detection/bronze').optimize().executeCompaction();
          spark.read.format('delta').load('hdfs://labsoe-17:9000/lakehouse/fraud_detection/silver/transactions').optimize().executeCompaction();
          "
        """
    )
