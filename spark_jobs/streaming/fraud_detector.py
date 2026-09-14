import os
import sys
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, to_json, struct, abs as spark_abs, current_timestamp, lit, when, to_timestamp,
    unix_timestamp, unix_millis, coalesce, count, max as spark_max, sum as spark_sum, countDistinct, avg, stddev, array
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, TimestampType
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
    .config("spark.databricks.delta.synchronousCheckpoints.enabled", "false") \
    .config("spark.cores.max", "4") \
    .getOrCreate()


spark.sparkContext.setLogLevel("ERROR")

# Configure HDFS paths
model_path = "/lakehouse/fraud_detection/models/gbt_fraud_model"
candidate_model_path = "/lakehouse/fraud_detection/models/candidate_gbt_model"
checkpoint_path = "/lakehouse/fraud_detection/checkpoints/realtime_fraud_detector"
bronze_transactions_path = "/lakehouse/fraud_detection/bronze/transactions"
gold_risk_scores_path = "/lakehouse/fraud_detection/gold/risk_scores"
silver_states_path = "/lakehouse/fraud_detection/silver/customer_states"

print("Loading trained GBT Pipeline Model from HDFS...")
try:
    model = PipelineModel.load(model_path)
    print(f"Successfully loaded production model from {model_path}")
except Exception as e_mod:
    print(f"Production model not found at {model_path} ({e_mod}). Trying candidate model at {candidate_model_path}...")
    model = PipelineModel.load(candidate_model_path)

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

print("Reading real-time transaction stream from Kafka...")
kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "192.168.80.200:9092") \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

parsed_df = kafka_stream_df.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("event_time", to_timestamp(col("timestamp"))) \
    .withWatermark("event_time", "1 minute")

def process_microbatch(microBatchDF, batchId):
    if microBatchDF.rdd.isEmpty():
        return

    batch_count = microBatchDF.count()

    # 1. Stream-Static Join with silver.customer_states for historical features
    if DeltaTable.isDeltaTable(spark, silver_states_path):
        raw_states = spark.read.format("delta").load(silver_states_path)
        if "account_id" not in raw_states.columns and "source_account" in raw_states.columns:
            raw_states = raw_states.withColumnRenamed("source_account", "account_id")
        elif "source_account" in raw_states.columns:
            raw_states = raw_states.drop("source_account")
        state_cols = ["account_id"]
        for c in ["trans_count_total", "total_amount_24h", "avg_amount_30d"]:
            if c in raw_states.columns:
                state_cols.append(c)
        states_df = raw_states.select(*state_cols)
    else:
        states_df = spark.createDataFrame([], StructType([
            StructField("account_id", StringType(), True),
            StructField("trans_count_total", IntegerType(), True),
            StructField("total_amount_24h", DoubleType(), True),
            StructField("avg_amount_30d", DoubleType(), True)
        ]))

    joined_df = microBatchDF.join(
        states_df,
        microBatchDF.source_account == states_df.account_id,
        "left"
    )

    # 2. Compute ML inference features (Matching build_training_set.py logic to prevent Training-Serving Skew)
    error_dest_expr = when(
        col("trans_type").isin("TRANSFER", "PAYMENT"),
        spark_abs((col("old_balance_dest") + col("amount")) - col("new_balance_dest"))
    ).otherwise(lit(0.0))

    features_df = joined_df \
        .withColumn("trans_count_total", coalesce(col("trans_count_total"), lit(0)) + lit(1)) \
        .withColumn("sum_amount_prev", coalesce(col("total_amount_24h"), lit(0.0))) \
        .withColumn("avg_amount_prev", coalesce(col("avg_amount_30d"), col("amount"))) \
        .withColumn("amount_to_avg_ratio", col("amount") / when(col("avg_amount_prev") > 0, col("avg_amount_prev")).otherwise(col("amount"))) \
        .withColumn("error_balance_source", spark_abs((col("old_balance_source") - col("amount")) - col("new_balance_source"))) \
        .withColumn("error_balance_dest", error_dest_expr) \
        .na.fill({
            "trans_count_total": 1,
            "sum_amount_prev": 0.0,
            "avg_amount_prev": 0.0,
            "amount_to_avg_ratio": 1.0,
            "error_balance_source": 0.0,
            "error_balance_dest": 0.0,
            "old_balance_source": 0.0,
            "new_balance_source": 0.0,
            "old_balance_dest": 0.0,
            "new_balance_dest": 0.0
        })

    # 3. Execute ML Inference
    scored_df = model.transform(features_df) \
        .withColumn("prob_fraud", vector_to_array(col("probability"))[1])

    fraud_alerts_df = scored_df.filter(col("prediction") == 1.0).cache()
    fraud_count = fraud_alerts_df.count()

    print(f"[MicroBatch {batchId}] Processed {batch_count} transactions | Fraud Alerts: {fraud_count}")


    # A. Raw transaction ingestion to bronze.transactions is handled by dedicated bronze_ingestion.py job.


    # B. Append scored records to gold.risk_scores with top risk contribution factors
    try:
        latency_calc = unix_millis(current_timestamp()) - unix_millis(to_timestamp(col("received_at")))
        gold_df = scored_df.select(
            col("transaction_id"),
            col("source_account"),
            col("dest_account"),
            col("trans_type"),
            col("amount"),
            col("channel"),
            coalesce(col("timestamp").cast("string"), current_timestamp().cast("string")).alias("timestamp"),
            coalesce(col("received_at").cast("string"), current_timestamp().cast("string")).alias("received_at"),
            col("prob_fraud").cast("double").alias("risk_score"),
            when(col("prediction") == 1.0, lit("PENDING")).otherwise(lit("CLEARED")).alias("inspection_status"),
            lit("GBT_v1.0").alias("model_version"),
            when(latency_calc < lit(0), lit(0)).otherwise(latency_calc).alias("latency_ms"),
            array(
                struct(lit("amount_to_avg_ratio").alias("name"), col("amount_to_avg_ratio").cast("double").alias("contribution")),
                struct(lit("error_balance_source").alias("name"), col("error_balance_source").cast("double").alias("contribution")),
                struct(lit("error_balance_dest").alias("name"), col("error_balance_dest").cast("double").alias("contribution"))
            ).alias("top_risk_factors"),
            current_timestamp().alias("scored_at")
        )
        gold_df.write.format("delta").mode("append").option("mergeSchema", "true").save(gold_risk_scores_path)
    except Exception as e_gold:
        print(f"[Gold Error] {e_gold}")

    # C. Delta MERGE account state aggregates into silver.customer_states
    try:
        batch_stats = microBatchDF.groupBy("source_account").agg(
            count("transaction_id").alias("b_tx_count"),
            spark_sum("amount").alias("b_sum_amount"),
            spark_max("event_time").alias("b_last_time"),
            spark_max("new_balance_source").alias("b_last_balance")
        ).withColumnRenamed("source_account", "account_id")

        if DeltaTable.isDeltaTable(spark, silver_states_path):
            deltaTable = DeltaTable.forPath(spark, silver_states_path)
            deltaTable.alias("target").merge(
                batch_stats.alias("source"),
                "target.account_id = source.account_id"
            ).whenMatchedUpdate(set={
                "tx_count_24h": col("target.tx_count_24h") + col("source.b_tx_count"),
                "trans_count_total": col("target.trans_count_total") + col("source.b_tx_count"),
                "total_amount_24h": col("target.total_amount_24h") + col("source.b_sum_amount"),
                "last_active_time": col("source.b_last_time"),
                "last_known_balance": col("source.b_last_balance"),
                "updated_at": current_timestamp()
            }).whenNotMatchedInsert(values={
                "account_id": col("source.account_id"),
                "tx_count_1h": col("source.b_tx_count"),
                "tx_count_24h": col("source.b_tx_count"),
                "tx_count_7d": col("source.b_tx_count"),
                "trans_count_total": col("source.b_tx_count"),
                "total_amount_24h": col("source.b_sum_amount"),
                "avg_amount_30d": col("source.b_sum_amount") / col("source.b_tx_count"),
                "stddev_amount_30d": lit(0.0),
                "unique_dest_accounts_24h": lit(1),
                "frequent_tx_hours": array(lit(8), lit(12), lit(20)),
                "last_active_time": col("source.b_last_time"),
                "last_known_balance": col("source.b_last_balance"),
                "updated_at": current_timestamp()
            }).execute()
        else:
            init_df = batch_stats.select(
                col("account_id"),
                col("b_tx_count").alias("tx_count_1h"),
                col("b_tx_count").alias("tx_count_24h"),
                col("b_tx_count").alias("tx_count_7d"),
                col("b_tx_count").alias("trans_count_total"),
                col("b_sum_amount").alias("total_amount_24h"),
                (col("b_sum_amount") / col("b_tx_count")).alias("avg_amount_30d"),
                lit(0.0).alias("stddev_amount_30d"),
                lit(1).alias("unique_dest_accounts_24h"),
                array(lit(8), lit(12), lit(20)).alias("frequent_tx_hours"),
                col("b_last_time").alias("last_active_time"),
                col("b_last_balance").alias("last_known_balance"),
                current_timestamp().alias("updated_at")
            )
            init_df.write.format("delta").mode("overwrite").save(silver_states_path)
    except Exception as e_merge:
        print(f"[Merge Error] {e_merge}")

    # D. Publish alerts to Kafka topic 'alerts'
    if fraud_count > 0:
        try:
            kafka_payload = fraud_alerts_df.select(
                col("transaction_id").cast("string").alias("key"),
                to_json(struct(
                    col("transaction_id"),
                    col("source_account"),
                    col("dest_account"),
                    col("trans_type"),
                    col("amount"),
                    col("channel"),
                    col("prob_fraud").alias("risk_score"),
                    col("prob_fraud").alias("fraud_probability"),
                    current_timestamp().cast("string").alias("alert_generated_at")
                )).cast("string").alias("value")
            )

            kafka_payload.write \
                .format("kafka") \
                .option("kafka.bootstrap.servers", "192.168.80.200:9092") \
                .option("topic", "alerts") \
                .save()
            print(f"   [Kafka] Successfully published {fraud_count} fraud alerts to topic 'alerts'")
        except Exception as e_kafka:
            print(f"[Kafka Error] {e_kafka}")

    fraud_alerts_df.unpersist()

print("Starting Structured Streaming Query (trigger 10s)...")
query = parsed_df.writeStream \
    .queryName("Fraud_Detector_ForeachBatch") \
    .option("checkpointLocation", checkpoint_path) \
    .trigger(processingTime="10 seconds") \
    .foreachBatch(process_microbatch) \
    .start()

spark.streams.awaitAnyTermination()