"""
SparkSession Provider for FastAPI Backend
Integrates Delta Lake and HDFS with singleton lifecycle management.
"""

import os
import sys
from typing import Optional
from pyspark.sql import SparkSession
from app.core.config import settings

_spark_session: Optional[SparkSession] = None

def get_spark_session() -> SparkSession:
    """
    Returns an active singleton SparkSession configured for Delta Lake and HDFS.
    Reuses existing session across requests to minimize JVM overhead.
    """
    global _spark_session
    
    if _spark_session is not None and not _spark_session._jsc.sc().isStopped():
        return _spark_session
        
    try:
        # Ensure environment variables are loaded
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
        
        builder = SparkSession.builder \
            .appName(f"FraudDetection_WebApp_{os.getpid()}") \
            .master("local[2]") \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
            .config("spark.hadoop.fs.defaultFS", settings.HDFS_URL) \
            .config("spark.driver.memory", "1g") \
            .config("spark.sql.shuffle.partitions", "4") \
            .config("spark.ui.enabled", "false")
            
        if available_jars:
            builder = builder.config("spark.jars", ",".join(available_jars))
        else:
            builder = builder.config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0")

        _spark_session = builder.getOrCreate()
        _spark_session.sparkContext.setLogLevel("WARN")
        return _spark_session
    except Exception as e:
        import traceback
        print(f"[SparkSession Error] Could not initialize PySpark session: {e}", file=sys.stderr)
        traceback.print_exc()
        raise e