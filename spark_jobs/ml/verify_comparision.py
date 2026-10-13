from pyspark.sql import SparkSession
from pyspark.sql.functions import col, desc

spark = SparkSession.builder \
    .appName("Read_Imbalance_Comparison") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

PATH = "/lakehouse/fraud_detection/gold/imbalance_strategy_comparison"

df = spark.read.format("delta").load(PATH)

print("\n" + "=" * 80)
print("  IMBALANCE STRATEGY COMPARISON")
print("=" * 80)

df.printSchema()
print(f"\nTotal rows: {df.count()}\n")

# Bảng so sánh gọn
df.select(
    "strategy",
    "precision_at_200",
    "pr_auc",
    "roc_auc",
    "fraud_detected_in_top200",
    "evaluated_at"
).orderBy(desc("precision_at_200")) \
 .show(truncate=False, vertical=False)

# Best strategy
best = df.orderBy(desc("precision_at_200")).first()
if best:
    print("\n" + "=" * 80)
    print("  BEST STRATEGY")
    print("=" * 80)
    print(f"  Strategy:       {best['strategy']}")
    print(f"  P@200:          {best['precision_at_200']:.4f}")
    print(f"  PR-AUC:         {best['pr_auc']:.4f}")
    print(f"  ROC-AUC:        {best['roc_auc']:.4f}")
    print(f"  Frauds caught:  {best['fraud_detected_in_top200']}")
    print("=" * 80)

spark.stop()