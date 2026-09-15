import os
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import (
    from_json, col, to_json, struct, abs as spark_abs,
    current_timestamp, lit, when, to_timestamp,
    unix_millis, coalesce, count, max as spark_max,
    sum as spark_sum, avg as spark_avg, desc
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType
)
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from delta.tables import DeltaTable

spark = SparkSession.builder \
    .appName("FraudDetection_Realtime_Detector") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.databricks.delta.schema.autoMerge.enabled", "true") \
    .config("spark.databricks.delta.optimisticTransaction.conflictRetry.attempts", "5") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

MODEL_PATH        = "hdfs:///lakehouse/fraud_detection/models/gbt_fraud_model"
CANDIDATE_PATH    = "hdfs:///lakehouse/fraud_detection/models/candidate_gbt_model"
CHECKPOINT_PATH   = "hdfs:///lakehouse/fraud_detection/checkpoints/realtime_fraud_detector"
SILVER_STATES     = "hdfs:///lakehouse/fraud_detection/silver/customer_states"
GOLD_RISK_SCORES  = "hdfs:///lakehouse/fraud_detection/gold/risk_scores"
KAFKA_BROKERS     = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.80.200:9092")

print("Loading trained GBT Pipeline Model...")
try:
    model = PipelineModel.load(MODEL_PATH)
    print(f"Loaded production model from {MODEL_PATH}")
except Exception as e:
    print(f"Production model unavailable ({e}), loading candidate.")
    model = PipelineModel.load(CANDIDATE_PATH)

schema = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("source_account", StringType(), True),
    StructField("dest_account", StringType(), True),
    StructField("trans_type", StringType(), True),
    StructField("amount", DoubleType(), True),
    StructField("old_balance_source", DoubleType(), True),
    StructField("new_balance_source", DoubleType(), True),
    StructField("old_balance_dest", DoubleType(), True),
    StructField("new_balance_dest", DoubleType(), True),
    StructField("channel", StringType(), True),
    StructField("is_fraud_label", IntegerType(), True),
    StructField("timestamp", StringType(), True),
    StructField("received_at", StringType(), True),
    StructField("partition_date", StringType(), True)
])

kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKERS) \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

parsed_df = kafka_stream_df \
    .select(
        col("timestamp").alias("kafka_ts_ms"), 
        col("value").cast("string").alias("json_payload")
    ) \
    .select(
        col("kafka_ts_ms"),
        from_json(col("json_payload"), schema).alias("data")
    ) \
    .select("kafka_ts_ms", "data.*") \
    .withColumn("event_time", to_timestamp(col("timestamp"))) \
    .withWatermark("event_time", "1 minute")


def process_microbatch(micro_batch_df, batch_id):
    if micro_batch_df.rdd.isEmpty():
        return

    batch_size = micro_batch_df.count()

    # 1. Load state TRƯỚC khi update — đây là điểm mấu chốt để tránh
    if DeltaTable.isDeltaTable(spark, SILVER_STATES):
        states_df = spark.read.format("delta").load(SILVER_STATES).select(
            col("account_id"),
            col("trans_count_total").alias("s_trans_count_total"),
            col("sum_amount_history").alias("s_sum_amount_prev"),
            col("avg_amount_history").alias("s_avg_amount_prev"),
            col("tx_count_24h").alias("s_trans_count_24h"),
            col("total_amount_24h").alias("s_sum_amount_24h"),
            col("tx_count_1h").alias("s_trans_count_1h")
        )
    else:
        states_df = spark.createDataFrame([], StructType([
            StructField("account_id", StringType(), True),
            StructField("s_trans_count_total", IntegerType(), True),
            StructField("s_sum_amount_prev", DoubleType(), True),
            StructField("s_avg_amount_prev", DoubleType(), True),
            StructField("s_trans_count_24h", IntegerType(), True),
            StructField("s_sum_amount_24h", DoubleType(), True),
            StructField("s_trans_count_1h", IntegerType(), True)
        ]))

    joined = micro_batch_df.join(
        states_df,
        micro_batch_df.source_account == states_df.account_id,
        "left"
    )


    # 2. Feature engineering — PHẢI khớp build_training_set.py

    error_dest_expr = when(
        col("trans_type").isin("TRANSFER", "PAYMENT"),
        spark_abs((col("old_balance_dest") + col("amount")) - col("new_balance_dest"))
    ).otherwise(lit(0.0))

    features_df = joined \
        .withColumn("trans_count_total", coalesce(col("s_trans_count_total"), lit(0))) \
        .withColumn("sum_amount_prev",  coalesce(col("s_sum_amount_prev"),  lit(0.0))) \
        .withColumn("avg_amount_prev",
            when(col("trans_count_total") > 0, col("sum_amount_prev") / col("trans_count_total"))
            .otherwise(lit(0.0))
        ) \
        .withColumn("amount_to_avg_ratio",
            when(col("avg_amount_prev") > 0, col("amount") / col("avg_amount_prev"))
            .otherwise(lit(1.0))
        ) \
        .withColumn("trans_count_24h", coalesce(col("s_trans_count_24h"), lit(0))) \
        .withColumn("sum_amount_24h",  coalesce(col("s_sum_amount_24h"),  lit(0.0))) \
        .withColumn("trans_count_1h",  coalesce(col("s_trans_count_1h"),  lit(0))) \
        .withColumn("error_balance_source",
            spark_abs((col("old_balance_source") - col("amount")) - col("new_balance_source"))
        ) \
        .withColumn("error_balance_dest", error_dest_expr) \
        .na.fill({
            "amount": 0.0,
            "old_balance_source": 0.0, "new_balance_source": 0.0,
            "old_balance_dest": 0.0,   "new_balance_dest": 0.0,
            "trans_type": "UNKNOWN",   "channel": "UNKNOWN"
        })

    # 3. Inference
    scored = model.transform(features_df) \
        .withColumn("prob_fraud", vector_to_array(col("probability"))[1]) \
        .withColumn("scored_at", current_timestamp())

    fraud_alerts = scored.filter(col("prediction") == 1.0).cache()
    fraud_count = fraud_alerts.count()
    print(f"[MicroBatch {batch_id}] processed {batch_size} | fraud alerts {fraud_count}")

    # 4. Write gold.risk_scores
    gold_df = scored.select(
        col("transaction_id"),
        col("source_account"),
        col("dest_account"),
        col("trans_type"),
        col("amount"),
        col("channel"),
        col("event_time").alias("timestamp"),
        col("received_at"),
        col("prob_fraud").cast("double").alias("risk_score"),
        when(col("prediction") == 1.0, lit("PENDING")).otherwise(lit("CLEARED")).alias("inspection_status"),
        lit("GBT_v1.0").alias("model_version"),
        (unix_millis(col("scored_at")) - col("kafka_ts_ms")).cast("long").alias("latency_ms"),
        struct(
            lit("amount_to_avg_ratio").alias("name"),
            (col("amount_to_avg_ratio") - lit(1.0)).cast("double").alias("contribution")
        ).alias("f_amount_ratio"),
        struct(
            lit("error_balance_source").alias("name"),
            col("error_balance_source").cast("double").alias("contribution")
        ).alias("f_err_src"),
        struct(
            lit("error_balance_dest").alias("name"),
            col("error_balance_dest").cast("double").alias("contribution")
        ).alias("f_err_dst"),
        col("scored_at")
    ).select(
        "*",
        struct(col("f_amount_ratio"), col("f_err_src"), col("f_err_dst")).alias("top_risk_factors")
    ).drop("f_amount_ratio", "f_err_src", "f_err_dst")

    gold_df.write.format("delta").mode("append") \
        .option("mergeSchema", "true") \
        .save(GOLD_RISK_SCORES)

    # 5. Update state SAU khi đã score (đảm bảo point-in-time cho batch sau)

    batch_stats = micro_batch_df.groupBy("source_account").agg(
        count("transaction_id").alias("b_count"),
        spark_sum("amount").alias("b_sum"),
        spark_max("event_time").alias("b_last_time"),
        spark_max("new_balance_source").alias("b_last_balance")
    ).withColumnRenamed("source_account", "account_id")

    if DeltaTable.isDeltaTable(spark, SILVER_STATES):
        delta_t = DeltaTable.forPath(spark, SILVER_STATES)
        delta_t.alias("t").merge(
            batch_stats.alias("s"),
            "t.account_id = s.account_id"
        ).whenMatchedUpdate(set={
            "trans_count_total": col("t.trans_count_total") + col("s.b_count"),
            "sum_amount_history": col("t.sum_amount_history") + col("s.b_sum"),
            "avg_amount_history": (col("t.sum_amount_history") + col("s.b_sum")) /
                                  (col("t.trans_count_total") + col("s.b_count")),
            "tx_count_1h":  col("t.tx_count_1h")  + col("s.b_count"),
            "tx_count_24h": col("t.tx_count_24h") + col("s.b_count"),
            "tx_count_7d":  col("t.tx_count_7d")  + col("s.b_count"),
            "total_amount_24h": col("t.total_amount_24h") + col("s.b_sum"),
            "last_active_time": col("s.b_last_time"),
            "last_known_balance": col("s.b_last_balance"),
            "updated_at": current_timestamp()
        }).whenNotMatchedInsert(values={
            "account_id": col("s.account_id"),
            "trans_count_total": col("s.b_count"),
            "sum_amount_history": col("s.b_sum"),
            "avg_amount_history": col("s.b_sum") / col("s.b_count"),
            "stddev_amount_history": lit(0.0),
            "unique_dest_accounts": lit(1),
            "tx_count_1h":  col("s.b_count"),
            "tx_count_24h": col("s.b_count"),
            "tx_count_7d":  col("s.b_count"),
            "total_amount_24h": col("s.b_sum"),
            "frequent_tx_hours": lit(None).cast("array<int>"),
            "last_active_time": col("s.b_last_time"),
            "last_known_balance": col("s.b_last_balance"),
            "updated_at": current_timestamp()
        }).execute()

    # 6. Publish alerts to Kafka
    if fraud_count > 0:
        alert_payload = fraud_alerts.select(
            col("transaction_id").cast("string").alias("key"),
            to_json(struct(
                col("transaction_id"),
                col("source_account"),
                col("dest_account"),
                col("trans_type"),
                col("amount"),
                col("prob_fraud").alias("risk_score")
            )).cast("string").alias("value")
        )
        alert_payload.write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BROKERS) \
            .option("topic", "alerts") \
            .save()

    fraud_alerts.unpersist()


query = parsed_df.writeStream \
    .queryName("Fraud_Detector_ForeachBatch") \
    .option("checkpointLocation", CHECKPOINT_PATH) \
    .trigger(processingTime="10 seconds") \
    .foreachBatch(process_microbatch) \
    .start()

spark.streams.awaitAnyTermination()