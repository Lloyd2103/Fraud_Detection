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
        os.environ.setdefault("SPARK_HOME", "/home/master/spark")
        
        builder = SparkSession.builder \
            .appName(f"FraudDetection_WebApp_{os.getpid()}") \
            .master("local[2]") \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
            .config("spark.hadoop.fs.defaultFS", settings.HDFS_URL) \
            .config("spark.driver.memory", "1g") \
            .config("spark.sql.shuffle.partitions", "4") \
            .config("spark.ui.enabled", "false")
            
        _spark_session = builder.getOrCreate()
        _spark_session.sparkContext.setLogLevel("WARN")
        return _spark_session
    except Exception as e:
        print(f"[SparkSession Warning] Could not initialize PySpark session directly: {e}", file=sys.stderr)
        raise e