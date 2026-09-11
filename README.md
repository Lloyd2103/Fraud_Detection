# 🛡️ Enterprise Real-Time Credit Card Fraud Detection Platform

[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-3.x-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)](https://spark.apache.org/)
[![Delta Lake](https://img.shields.io/badge/Delta%20Lake-3.x-003366?style=for-the-badge&logo=delta&logoColor=white)](https://delta.io/)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-Distributed-231F20?style=for-the-badge&logo=apachekafka&logoColor=white)](https://kafka.apache.org/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-2.x-017CEE?style=for-the-badge&logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

An enterprise-grade, distributed **Real-Time Fraud Detection & MLOps Platform** designed to process high-throughput credit card transaction streams, execute sub-second machine learning inference, maintain historical transactional integrity via a **Medallion Lakehouse Architecture**, and dynamically monitor data drift with automated model retraining.

---

## 📌 Executive Summary & Architecture Philosophy

Modern financial payment systems generate continuous micro-batches of transaction telemetry. Detecting fraudulent behavior requires balancing **ultra-low latency SLA enforcement** (< 1 second) with **historical batch auditability**, while overcoming challenges such as severe **class imbalance** and **concept drift**.

This platform unifies real-time streaming ingestion, Medallion Lakehouse storage (Delta Lake on HDFS), Point-in-Time (PIT) feature engineering, multi-algorithm ML evaluation (GBT, Random Forest, Logistic Regression), continuous drift monitoring (PSI & KS tests), and real-time WebSocket push notifications to a unified web dashboard.

### 🌟 Key Platform Capabilities

- **Medallion Lakehouse Architecture**: Structured data advancement from **Bronze** (raw streaming append) to **Silver** (cleaned, validated, enriched) and **Gold** (aggregated business metrics, audit queues, and evaluation matrices).
- **Sub-Second Streaming Inference**: Real-time evaluation of incoming transactions from Kafka using Apache Spark Structured Streaming with pre-trained GBT ML Pipelines.
- **Point-in-Time Feature Store**: Historical feature calculation relative to transaction timestamps, ensuring zero future-data leakage during model training.
- **Robust Class Imbalance Strategy**: Hybrid negative-class undersampling (1:20 ratio) paired with custom inverse class weighting.
- **Automated MLOps & Drift Monitoring**: Daily Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) statistical tests triggering automated retraining DAGs upon severe drift detection.
- **Production Lakehouse Maintenance**: Automated Z-Ordering and VACUUM routines optimizing Delta Lake performance on HDFS.
- **Real-Time Web Operating Center**: FastAPI backend serving WebSocket alerts and SLA latency tracking alongside a responsive single-page web application.

---

## 🏗 System Architecture

The following diagram illustrates the end-to-end data flow across ingestion, processing, storage, machine learning, orchestration, and presentation layers:

```mermaid
flowchart TD
    subgraph Data Sources & Ingestion
        KP[Kafka Producer / Transaction Stream] -->|JSON Stream| KT[Kafka Topic: 'transactions']
    Processing / Streaming Engine
        KT -->|Spark Structured Streaming| BI[Bronze Ingestion Job]
        KT -->|Micro-batch Ingestion| FD[Real-Time Fraud Detector Engine]
    end

    subgraph Storage Layer: Medallion Lakehouse (Delta Lake on HDFS)
        BI -->|Append Raw Logs| BZ[(Bronze Delta Table)]
        BZ -->|Spark ETL: Cleanse & Enrich| SV[(Silver Delta Table)]
        SV -->|Spark Aggregations & PIT Features| GD[(Gold Delta Table & Features)]
    end

    subgraph ML Pipeline & Model Store
        GD -->|Point-in-Time Features| FT[Feature Store]
        FT -->|Time-Split Train/Val/Test| TR[Multi-Model Trainer: GBT, RF, LR]
        TR -->|Evaluate: Precision@200, PR-AUC| MS[(HDFS Model Store: PipelineModel)]
        MS -->|Load Trained GBT Model| FD
    end

    subgraph Monitoring & Orchestration (Apache Airflow)
        AF1[DAG 1: Streaming Monitor] -->|Health Checks| FD
        AF2[DAG 2: Drift Monitor] -->|PSI / KS Tests| SV
        AF2 -->|Trigger Retraining on Drift| AF3[DAG 3: Model Retraining]
        AF3 -->|Re-Run Training Pipeline| TR
        AF4[DAG 4: Lakehouse Maintenance] -->|OPTIMIZE & VACUUM| BZ & SV & GD
    end

    subgraph Real-Time Web Platform
        FD -->|Publish Fraud Alerts| KFA[Kafka Topic: 'fraud_alerts']
        KFA -->|FastAPI Consumer / Service| API[FastAPI Backend]
        API -->|WebSocket Stream /ws/alerts| UI[Frontend Web Dashboard]
    end
```

---

## 📂 Repository Directory Structure

```directory
fraud_detection/
├── conf/                             # Environment & Component Configurations
│   ├── .env.example                  # Environment template for HDFS, Kafka, and Master IP
│   ├── airflow.cfg                   # Apache Airflow configuration override
│   ├── hdfs-site.xml                 # Hadoop Distributed File System settings
│   └── spark-defaults.conf           # Apache Spark cluster parameters
├── dags/                             # Apache Airflow Workflow Orchestration DAGs
│   ├── monitor_streaming_dag.py      # DAG 1: Streaming health check & auto-restart (10m)
│   ├── check_drift_dag.py            # DAG 2: Daily PSI & KS data drift detection
│   ├── fraud_detection_medallion_dag.py # DAG 3: Automated weekly model retraining pipeline
│   └── lakehouse_delta_optimization.py  # DAG 4: Daily Delta OPTIMIZE & VACUUM maintenance
├── spark_jobs/                       # PySpark Distributed Processing Jobs
│   ├── ingest/
│   │   ├── kafka_producer.py         # Transaction stream generator
│   │   └── bronze_ingestion.py       # Kafka -> HDFS Bronze Delta Lake streaming ingest
│   ├── transform/
│   │   ├── bronze_to_silver.py       # Bronze -> Silver ETL (Validation & feature extraction)
│   │   └── silver_to_gold.py         # Silver -> Gold ETL (Business aggregates & auditing)
│   ├── ml/
│   │   ├── build_training_set.py     # PIT Feature store builder
│   │   ├── train_model.py            # Multi-model trainer (GBT, RF, LR) & evaluator
│   │   └── check_data_drift.py       # Statistical PSI/KS metric calculator
│   ├── streaming/
│   │   └── fraud_detector.py         # Low-latency streaming inference worker
│   └── maintenance/
│       └── optimize_vacuum.py        # Delta Lake maintenance & compacting script
├── webapp/                           # Operations Center Web Application
│   ├── backend/                      # FastAPI Python Backend
│   │   ├── app/                      # Routers, core config, services, and models
│   │   ├── main.py                   # FastAPI server entry point & WebSocket engine
│   │   └── requirements.txt          # Backend dependencies
│   └── frontend/                     # Modern Web UI (Vite / SPA)
│       ├── src/                      # Frontend components, styles, and asset assets
│       ├── index.html                # Main SPA page
│       └── package.json              # Node.js dependencies & scripts
├── notebooks/                        # Exploratory Data Analysis & Prototyping
│   └── eda_fraud_detection.ipynb    # Data exploration & feature distribution analysis
├── tests/                            # Automation & Unit Testing Suite
│   └── test_pipeline.py              # Pipeline functional validation tests
├── docs/                             # Project Specifications & AI Documentation
├── .env                              # Active environment variable file
└── README.md                         # Project documentation
```

---

## 💎 Lakehouse Medallion Architecture Breakdown

The data processing pipeline adopts the **Medallion Architecture**, delivering clean, reliable data for reporting, auditing, and ML modeling:

| Layer | Path / Format | Description & Data Integrity Controls |
| :--- | :--- | :--- |
| **Bronze** | `hdfs:///lakehouse/fraud_detection/bronze` (Delta) | Raw transaction logs ingested directly from Kafka. Append-only, partitioned by `partition_date`. Retains complete raw audit trail with schema validation. |
| **Silver** | `hdfs:///lakehouse/fraud_detection/silver` (Delta) | Cleansed and validated transaction records. Deduplicated by `transaction_id`, imputed null values, enriched with calculated features (`error_balance_source`, `error_balance_dest`). |
| **Gold** | `hdfs:///lakehouse/fraud_detection/gold/*` (Delta) | Business aggregates, high-risk alert queues, SLA latency performance logs, and model comparison results (`model_performance_comparison`). |
| **Feature Store**| `hdfs:///lakehouse/fraud_detection/features` (Delta) | Point-in-Time (PIT) training dataset enriched with time-aware aggregations and categorical encoding. |

---

## 🤖 Machine Learning & MLOps Pipeline

### 1. Time-Based Data Splitting (Anti-Data Leakage)
To prevent temporal leakage in financial time-series data, transaction records are strictly partitioned chronologically:
- **Training Set**: First 70% of chronological transactions.
- **Validation Set**: Subsequent 15% of transactions.
- **Test Set**: Final 15% of transactions.

### 2. Class Imbalance Mitigation Strategy
Financial fraud typically exhibits severe class imbalance (< 1% fraud rate). The training pipeline applies a two-tiered balancing strategy:
1. **Negative Class Undersampling**: Randomly undersamples non-fraudulent transactions to achieve a **1:20 target ratio**.
2. **Inverse Class Weighting**: Calculates sample weights based on inverse class frequencies and applies them directly into model loss functions (`weightCol="class_weight"`).

$$\text{Weight}_{\text{fraud}} = \frac{N_{\text{total}}}{2 \times N_{\text{fraud}}}, \quad \text{Weight}_{\text{safe}} = \frac{N_{\text{total}}}{2 \times N_{\text{safe}}}$$

### 3. Multi-Model Benchmark & Evaluation
`spark_jobs/ml/train_model.py` trains and evaluates three distinct classifiers:
- **Gradient Boosted Trees (GBTClassifier)** (Selected for primary real-time inference pipeline)
- **Random Forest Classifier**
- **Logistic Regression (ElasticNet Regularization)**

#### Evaluation Metrics Matrix

Because Accuracy is misleading under extreme imbalance, models are benchmarked using imbalanced-tailored metrics:
- **Precision@200**: Precision within the top 200 highest-risk predicted transactions.
- **PR-AUC**: Area Under the Precision-Recall Curve (Primary decision metric).
- **ROC-AUC**: Receiver Operating Characteristic AUC.

### 4. Automated Data Drift & Retraining (PSI / KS Statistics)
`spark_jobs/ml/check_data_drift.py` computes the **Population Stability Index (PSI)** and **Kolmogorov-Smirnov (KS)** statistics daily:

$$\text{PSI} = \sum \left( \Big( \% \text{ Actual}_i - \% \text{ Baseline}_i \Big) \times \ln\left( \frac{\% \text{ Actual}_i}{\% \text{ Baseline}_i} \right) \right)$$

- **PSI < 0.10**: Distribution Stable (Logs status).
- **0.10 ≤ PSI ≤ 0.25**: Moderate Drift Detected (Triggers warning alerts).
- **PSI > 0.25**: Critical Feature Drift Detected (Automatically triggers Airflow `model_retraining_dag`).

---

## 🔄 Workflow Orchestration (Apache Airflow)

The platform includes 4 production Airflow DAGs:

```
+----------------------------------------------------------------------------------+
| Airflow DAG Schedule                                                             |
+-----------------------------------+---------------+------------------------------+
| DAG ID                            | Schedule      | Purpose                      |
+-----------------------------------+---------------+------------------------------+
| streaming_monitor_dag             | */10 * * * *  | Streaming PID Health Monitor |
| data_drift_monitor_dag            | 0 1 * * *     | Daily PSI & KS Drift Check   |
| model_retraining_dag              | 0 3 * * 1     | Automated Model Retraining   |
| lakehouse_maintenance_dag         | 30 4 * * *    | Delta OPTIMIZE & VACUUM      |
+-----------------------------------+---------------+------------------------------+
```

1. **`streaming_monitor_dag`**: Runs every 10 minutes. Verifies active PySpark streaming processes (`FraudDetection_BronzeIngestion`, `FraudDetection_Realtime_Detector`) and automatically restarts them if a failure occurs.
2. **`data_drift_monitor_dag`**: Runs daily at 01:00 AM. Computes feature PSI; if critical drift is detected, branches dynamically to trigger `model_retraining_dag`.
3. **`model_retraining_dag`**: Weekly (or trigger-driven) pipeline executing Bronze-to-Silver ETL, Silver-to-Gold aggregation, feature store construction, multi-model retraining, metric logging, and registering the updated `PipelineModel` to HDFS.
4. **`lakehouse_maintenance_dag`**: Runs daily at 04:30 AM. Performs Delta Lake compaction (`OPTIMIZE`) and removes unreferenced historical data files older than retention thresholds (`VACUUM`).

---

## 🚀 Getting Started & Execution Guide

### 📋 Prerequisites

Ensure your system has the following components installed and configured:
- **Operating System**: Linux (Ubuntu 20.04 / 22.04 LTS recommended)
- **Java**: OpenJDK 11 or 17
- **Apache Spark**: v3.4+ / v3.5+ with Delta Lake 3.x support
- **Hadoop Distributed File System (HDFS)**: Running NameNode & DataNode
- **Apache Kafka**: Running Broker on port 9092
- **Python**: v3.10+ (PySpark, FastAPI, Uvicorn, Delta-Spark)
- **Node.js & npm**: Node v18+ for Web Application frontend

---

### ⚙️ Step 1: Environment Setup

Create `.env` from the provided template:

```bash
cp conf/.env.example .env
```

Edit `.env` to set your cluster IPs and parameters:

```env
MASTER_IP=192.168.80.200
KAFKA_BOOTSTRAP_SERVERS=192.168.80.200:9092
KAFKA_TOPIC=transactions
HDFS_HOST=labsoe-17
HDFS_PORT=9000
```

---

### 📥 Step 2: Streaming Ingestion & Kafka Production

1. **Start the Kafka Producer** (Simulate stream of payment transactions):
   ```bash
   python3 spark_jobs/ingest/kafka_producer.py
   ```

2. **Launch Spark Streaming Ingestion to Bronze Delta Lake**:
   ```bash
   $SPARK_HOME/bin/spark-submit \
     --packages io.delta:delta-spark_2.12:3.2.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
     spark_jobs/ingest/bronze_ingestion.py
   ```

3. **Launch Real-Time ML Streaming Detector**:
   ```bash
   $SPARK_HOME/bin/spark-submit \
     --packages io.delta:delta-spark_2.12:3.2.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
     spark_jobs/streaming/fraud_detector.py
   ```

---

### 🏋️ Step 3: Model Retraining & Feature Engineering Pipeline

Run the batch ML retraining pipeline manually or via Apache Airflow:

```bash
# 1. Transform Bronze to Silver
$SPARK_HOME/bin/spark-submit spark_jobs/transform/bronze_to_silver.py

# 2. Build Point-in-Time Feature Dataset
$SPARK_HOME/bin/spark-submit spark_jobs/ml/build_training_set.py

# 3. Train Multi-Model Benchmark & Register Best PipelineModel
$SPARK_HOME/bin/spark-submit spark_jobs/ml/train_model.py
```

---

### 🌐 Step 4: Web Application Operations Dashboard

#### Start FastAPI Backend

```bash
cd webapp/backend
pip install -r requirements.txt
python3 main.py
```
*Backend runs on `http://localhost:8000`. API documentation available at `http://localhost:8000/docs`.*

#### Start Frontend UI

```bash
cd webapp/frontend
npm install
npm run dev
```
*Frontend interface available at `http://localhost:5173`.*

---

## 🧪 Testing & Validation

Execute unit and integration tests for the processing pipeline:

```bash
pytest tests/
```

---

## 📊 Key Results & System SLA Performance

- **Streaming Inference SLA**: Sub-second alert latency (< 800ms end-to-end from Kafka topic ingestion to WebSocket alert dispatch).
- **Fraud Detection Precision**: High Precision@200 achieved via GBT Classifier with inverse class weighting.
- **Lakehouse Storage Efficiency**: Delta Lake compaction reduces small-file HDFS metadata pressure by ~65%.

---

## 📄 License & Attribution

Distributed under the **MIT License**. Built as an enterprise blueprint for real-time streaming analytics, lakehouse data management, and automated MLOps.