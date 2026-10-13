# State schema and helper definitions for stateful streaming with applyInPandasWithState
import json
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DoubleType, TimestampType, ArrayType, IntegerType
)

# 1. State schema (Single Source of Truth: flat struct stored in RocksDB per source_account)
STATE_SCHEMA = StructType([
    StructField("account_id",            StringType(), False),
    StructField("last_known_balance",    DoubleType(), True),
    StructField("last_event_ts",         TimestampType(), True),
    StructField("recent_events_json",    StringType(), True),   # Single source of truth (ring buffer)
    StructField("unique_dest_24h_json",  StringType(), True),   # Derived map {dest_account: first_seen_iso}, bounded at 200
    StructField("hour_histogram_json",   StringType(), True),   # Derived map {hour_str: count}, 24 fixed keys
])

# 2. Schema emitted by applyInPandasWithState (enriched with point-in-time features & post-tx snapshot)
FEATURE_OUTPUT_SCHEMA = StructType([
    StructField("transaction_id",                StringType(), False),
    StructField("source_account",                StringType(), True),
    StructField("dest_account",                  StringType(), True),
    StructField("trans_type",                    StringType(), True),
    StructField("channel",                       StringType(), True),
    StructField("timestamp",                     StringType(), True),
    StructField("received_at",                   StringType(), True),
    StructField("old_balance_source",            DoubleType(), True),
    StructField("new_balance_source",            DoubleType(), True),
    StructField("old_balance_dest",              DoubleType(), True),
    StructField("new_balance_dest",              DoubleType(), True),

    # ---- Core numerics & log ----
    StructField("amount",                        DoubleType(), True),
    StructField("log_amount",                    DoubleType(), True),

    # ---- Balance dynamics & Remaining funds ----
    StructField("balance_drain_ratio",           DoubleType(), True),
    StructField("remaining_balance_ratio",       DoubleType(), True),
    StructField("dest_to_source_bal_ratio",      DoubleType(), True),
    StructField("dest_is_merchant",              DoubleType(), True),
    StructField("is_drain_attempt",              DoubleType(), True),
    StructField("is_zero_dest_balance",          DoubleType(), True),
    StructField("amount_to_old_balance_ratio",   DoubleType(), True),

    # ---- Card Testing & Micro & Structuring ----
    StructField("is_micro_transaction",          DoubleType(), True),
    StructField("is_transfer_or_cashout",        DoubleType(), True),

    # ---- Window aggregates ----
    StructField("trans_count_1h",                DoubleType(), True),
    StructField("trans_count_24h",               DoubleType(), True),
    StructField("trans_count_7d",                DoubleType(), True),
    StructField("trans_count_1h_to_7d_ratio",    DoubleType(), True),
    StructField("sum_amount_24h",                DoubleType(), True),
    StructField("sum_amount_7d",                 DoubleType(), True),
    StructField("avg_amount_30d",                DoubleType(), True),
    StructField("stddev_amount_30d",             DoubleType(), True),
    StructField("unique_dest_accounts_24h",      DoubleType(), True),
    StructField("is_unusual_hour",               DoubleType(), True),

    # ---- Ratios & Deviations ----
    StructField("amount_to_avg_ratio",           DoubleType(), True),
    StructField("amount_to_sum_7d_ratio",        DoubleType(), True),
    StructField("amount_zscore_local",           DoubleType(), True),
    StructField("amount_diff_avg_30d",           DoubleType(), True),

    # ---- Time-since-last & Velocity & Mule ----
    StructField("seconds_since_last_transaction",DoubleType(), True),
    StructField("inbound_count_7d",              DoubleType(), True),
    StructField("inbound_amount_7d",             DoubleType(), True),
    StructField("inbound_to_outbound_ratio_7d",  DoubleType(), True),
    StructField("amount_to_dest_inbound_avg",    DoubleType(), True),
    StructField("prev_transaction_amount",       DoubleType(), True),
    StructField("amount_ratio_to_prev",          DoubleType(), True),
    StructField("is_rapid_fire",                 DoubleType(), True),
    StructField("is_atm_cashout",                DoubleType(), True),

    # ---- Cyclical ----
    StructField("hour_cos",                      DoubleType(), True),

    # ---- Section 2.4 State snapshot for Silver Lakehouse (Section 2.7) ----
    StructField("post_tx_count_1h",              LongType(), True),
    StructField("post_tx_count_24h",             LongType(), True),
    StructField("post_tx_count_7d",              LongType(), True),
    StructField("post_sum_amount_24h",           DoubleType(), True),
    StructField("post_avg_amount_30d",           DoubleType(), True),
    StructField("post_stddev_amount_30d",        DoubleType(), True),
    StructField("post_unique_dest_24h",          LongType(), True),
    StructField("frequent_tx_hours_json",        StringType(), True),
    # Monotonic processing sequence to solve out-of-order state selection in Sink 3
    StructField("batch_seq",                     LongType(), True),
])

