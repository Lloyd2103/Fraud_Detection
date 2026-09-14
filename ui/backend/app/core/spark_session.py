# Spark session singleton provider for reading and writing Delta tables
import os
import sys

# Ensure official PySpark from SPARK_HOME takes precedence over user site-packages
spark_home = os.getenv("SPARK_HOME", "/home/master/spark")
py4j_zip = os.path.join(spark_home, "python/lib/py4j-0.10.9.7-src.zip")
pyspark_path = os.path.join(spark_home, "python")

if os.path.exists(pyspark_path) and pyspark_path not in sys.path:
    sys.path.insert(0, py4j_zip)
    sys.path.insert(0, pyspark_path)

from pyspark.sql import SparkSession
from app.core.config import settings

class SparkClientManager:
    _instance = None

    @classmethod
    def get_spark(cls) -> SparkSession:
        # Check if existing Spark instance is stopped or null
        if cls._instance is not None:
            try:
                if cls._instance.sparkContext._jsc is None or cls._instance.sparkContext._jsc.sc().isStopped():
                    cls._instance = None
            except Exception:
                cls._instance = None

        if cls._instance is None:
            os.environ.setdefault("HADOOP_HOME", "/home/master/hadoop-3.5.0")
            os.environ.setdefault("HADOOP_CONF_DIR", "/home/master/hadoop-3.5.0/etc/hadoop")
            os.environ.setdefault("SPARK_HOME", "/home/master/spark")

            ivy_jars_dir = "/home/master/.ivy2/jars"
            delta_jars = [
                f"{ivy_jars_dir}/io.delta_delta-spark_2.12-3.1.0.jar",
                f"{ivy_jars_dir}/io.delta_delta-storage-3.1.0.jar",
                f"{ivy_jars_dir}/org.antlr_antlr4-runtime-4.9.3.jar"
            ]
            available_jars = [j for j in delta_jars if os.path.exists(j)]

            master_url = os.getenv("SPARK_MASTER", "local[2]")
            builder = SparkSession.builder \
                .appName("FraudDetection_UI_Backend") \
                .master(master_url) \
                .config("spark.driver.host", "127.0.0.1") \
                .config("spark.driver.bindAddress", "127.0.0.1") \
                .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
                .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
                .config("spark.databricks.delta.schema.autoMerge.enabled", "true") \
                .config("spark.hadoop.fs.defaultFS", settings.HDFS_BASE_URL) \
                .config("spark.driver.memory", "1g") \
                .config("spark.sql.shuffle.partitions", "4") \
                .config("spark.ui.enabled", "false")

            if available_jars:
                builder = builder.config("spark.jars", ",".join(available_jars))
            else:
                builder = builder.config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0")

            cls._instance = builder.getOrCreate()
            cls._instance.sparkContext.setLogLevel("ERROR")
        return cls._instance