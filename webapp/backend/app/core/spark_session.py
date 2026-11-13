"""Optional local Spark session helper (used only when the web app needs Spark)."""
import glob
import os
import sys
from typing import Optional

from pyspark.sql import SparkSession

from app.config.settings import settings

_spark_session: Optional[SparkSession] = None


def get_spark_session() -> SparkSession:
    global _spark_session

    if _spark_session is not None and not _spark_session._jsc.sc().isStopped():
        return _spark_session

    try:
        # Paths come from the environment; nothing machine-specific is hard-coded here.
        if settings.HADOOP_HOME:
            os.environ.setdefault("HADOOP_HOME", settings.HADOOP_HOME)
            os.environ.setdefault("HADOOP_CONF_DIR", os.path.join(settings.HADOOP_HOME, "etc", "hadoop"))
        if settings.SPARK_HOME:
            os.environ.setdefault("SPARK_HOME", settings.SPARK_HOME)

        ivy_jars_dir = os.getenv("IVY_JARS_DIR", os.path.join(os.path.expanduser("~"), ".ivy2", "jars"))
        available_jars = [
            j for pattern in (
                "io.delta_delta-spark_2.12-*.jar",
                "io.delta_delta-storage-*.jar",
                "org.antlr_antlr4-runtime-*.jar",
            )
            for j in glob.glob(os.path.join(ivy_jars_dir, pattern))
        ]

        builder = (
            SparkSession.builder
            .appName(f"FraudDetection_WebApp_{os.getpid()}")
            .master("local[2]")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .config("spark.hadoop.fs.defaultFS", settings.HDFS_URL)
            .config("spark.driver.memory", "1g")
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.ui.enabled", "false")
        )

        if available_jars:
            builder = builder.config("spark.jars", ",".join(sorted(available_jars)))
        else:
            builder = builder.config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0")

        _spark_session = builder.getOrCreate()
        _spark_session.sparkContext.setLogLevel("WARN")
        return _spark_session
    except Exception as e:
        import traceback
        print(f"[SparkSession Error] Could not initialize PySpark session: {e}", file=sys.stderr)
        traceback.print_exc()
        raise
