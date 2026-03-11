# Global Sports Footwear Sales Pipeline

A medallion architecture ETL pipeline that ingests global sports footwear sales data, validates and transforms it through Bronze → Silver → Gold layers, and computes KPIs using Apache Spark — all orchestrated by Apache Airflow and containerised with Docker.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Setup & Installation](#4-setup--installation)
5. [Pipeline Walkthrough](#5-pipeline-walkthrough)
6. [Data Dictionary](#6-data-dictionary)

---

## 1. Project Overview

**Dataset:** `global_sports_footwear_sales_2018_2026.csv`
- 30,000 rows of synthetic global sneaker sales data
- 18 columns covering orders, pricing, discounts, brands, channels, and countries
- Brands: ASICS, Reebok, Nike, New Balance, Adidas, Puma
- Countries: Germany, USA, India, UK, UAE, Pakistan
- Sales channels: Retail Store, Online
- Date format in source: `DD/MM/YYYY`

**What the pipeline does:**
1. Detects arrival of the CSV file
2. Ingests raw data into MySQL (Bronze layer)
3. Validates and transforms the data, writes clean data back to MySQL (Silver layer)
4. Copies silver data across to PostgreSQL (Gold layer staging)
5. Runs a Spark job to compute KPI aggregations, writing final gold tables back to PostgreSQL

---

## 2. Architecture

### Medallion Layers

```
CSV File
   │
   ▼
┌─────────────────────────────┐
│  BRONZE  (MySQL)            │
│  sports_footwear_sales_raw  │  Raw, unmodified ingestion
└─────────────────────────────┘
   │
   ▼  validate + transform
┌─────────────────────────────┐
│  SILVER  (MySQL)            │
│  sports_footwear_sales_clean│  Cleaned, typed, camelCase columns
└─────────────────────────────┘
   │
   ▼  copy to warehouse
┌──────────────────────────────────┐
│  GOLD  (PostgreSQL - analytics)  │
│  gold_brand_performance          │
│  gold_monthly_sales              │  KPI aggregations computed by Spark
│  gold_channel_performance        │
│  gold_country_performance        │
│  gold_overall_metrics            │
└──────────────────────────────────┘
```

### Infrastructure

| Service | Image | Purpose | Port |
|---|---|---|---|
| `airflow-apiserver` | Custom (see Dockerfile) | Airflow UI + API | 8080 |
| `airflow-scheduler` | Custom (see Dockerfile) | DAG scheduling | — |
| `airflow-init` | Custom (see Dockerfile) | One-time DB init | — |
| `postgres` | postgres:16 | Airflow metadata DB | 5432 (internal) |
| `mysql` | mysql:8.0 | Bronze + Silver layers | 3306 |
| `warehouse` | postgres:16 | Gold layer / analytics | 5433 |

### Custom Airflow Image

The stock Airflow image doesn't include Java or Spark. The `Dockerfile` does a two-stage build:
- **Stage 1:** Pulls Spark 3.5.1 from `apache/spark:3.5.1-python3`
- **Stage 2:** Copies Spark into the Airflow 2.8.1 image, installs OpenJDK 17, and installs Python dependencies

---

## 3. Project Structure

```
project-root/
│
├── airflow/
│   ├── dags/
│   │   ├── dag_sneaker_pipeline.py     # Main DAG definition
│   │   ├── spark_compute_kpis.py       # Spark KPI job (submitted by DAG)
│   │   └── scripts/
│   │       ├── __init__.py
│   │       ├── config.py               # Path configuration
│   │       ├── validate.py             # Data validation logic
│   │       └── transform.py            # Data transformation logic
│   ├── logs/
│   ├── config/
│   └── plugins/
│
├── data/
│   └── global_sports_footwear_sales_2018_2026.csv
│
├── jars/
│   ├── mysql-connector-j-9.6.0.jar     # MySQL JDBC driver for Spark
│   └── postgresql-42.7.9.jar           # PostgreSQL JDBC driver for Spark
│
├── sql/
│   ├── init_staging.sql                # MySQL schema (Bronze + Silver)
│   └── init_analytics.sql             # PostgreSQL schema (Gold)
│
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
└── .env
```

> **Note:** `scripts/` lives inside `airflow/dags/` so that the single volume mount `./airflow/dags:/opt/airflow/dags` covers the DAG, the Spark script, and the scripts package all at once. This is also why `from scripts.config import ...` resolves correctly — Airflow's working directory is `/opt/airflow/dags/`.

---

## 4. Setup & Installation

### Prerequisites

- Docker Desktop (with WSL2 backend on Windows)
- At least 6GB RAM allocated to Docker
- The two JDBC JAR files placed in `./jars/`:
  - `mysql-connector-j-9.6.0.jar`
  - `postgresql-42.7.9.jar`

### Step 1 — Clone / set up the project directory

Ensure your project folder matches the structure in [Section 3](#3-project-structure). Place the CSV in `./data/` and the JARs in `./jars/`.

### Step 2 — Configure the `.env` file

A `.env.example` file is included in the project root with all the required variables and placeholder values. Copy it and fill in your own values:

```bash
cp .env.example .env
```

### Step 3 — Build the custom image

```bash
docker compose build
```

This builds the custom Airflow+Spark image. Only needed on first run or after changes to `Dockerfile` or `requirements.txt`.

### Step 4 — Initialise Airflow

```bash
docker compose up airflow-init
```

This runs once to migrate the Airflow metadata DB and create the admin user. Wait for it to complete (exit code 0) before the next step.

### Step 5 — Start all services

```bash
docker compose up
```

Or to run in the background:

```bash
docker compose up -d
```

### Step 6 — Access the Airflow UI

Go to `http://localhost:8080` and log in with the credentials from your `.env` (`airflow` / `airflow` by default).

### Step 7 — Run the pipeline

1. Find the `sneaker_sales_pipeline` DAG in the UI
2. Toggle it from paused to active
3. Click **Trigger DAG** to run it manually

### Stopping everything

```bash
docker compose down
```

To also wipe all database volumes (full reset):

```bash
docker compose down -v
```

---

## 5. Pipeline Walkthrough

The DAG is defined in `dag_sneaker_pipeline.py` and runs on a `@daily` schedule. It has five tasks executed sequentially:

```
wait_for_csv >> ingest_csv_to_mysql >> validate_and_transform_data >> load_to_postgres >> compute_gold_kpis
```

---

### Task 1 — `wait_for_csv` (FileSensor)

Polls for the CSV file at the configured `DATA_PATH` every 30 seconds, timing out after 10 minutes. The pipeline won't proceed until the file is present.

- **Operator:** `FileSensor`
- **Polls:** `/opt/airflow/data/global_sports_footwear_sales_2018_2026.csv`
- **Poke interval:** 30s
- **Timeout:** 600s

---

### Task 2 — `ingest_csv_to_mysql` (PythonOperator)

Reads the raw CSV with pandas and loads it into the MySQL bronze table with no transformations at all — data goes in exactly as it is.

- **Reads from:** CSV file via pandas
- **Writes to:** `sports_footwear_sales_raw` (MySQL)
- **Strategy:** Truncate then append on every run (idempotent)
- **Connection:** `mysql_staging`

**What happens:**
1. `pd.read_csv()` reads all 30,000 rows
2. `TRUNCATE TABLE sports_footwear_sales_raw` clears any previous data
3. `df.to_sql(..., if_exists='append')` loads the fresh data

---

### Task 3 — `validate_and_transform_data` (PythonOperator)

Reads from the bronze table, runs validation and transformation logic defined in `scripts/validate.py` and `scripts/transform.py`, and writes the cleaned result to the MySQL silver table.

- **Reads from:** `sports_footwear_sales_raw` (MySQL)
- **Writes to:** `sports_footwear_sales_clean` (MySQL)
- **Connection:** `mysql_staging`

#### Validation (`validate.py`)

| Check | Action |
|---|---|
| Duplicate `order_id` | Drop duplicates, keep first |
| Missing `order_id`, `brand`, or `units_sold` | Drop the row |
| Non-numeric values in numeric columns | Coerce to NaN, drop rows where `units_sold` or `base_price_usd` is NaN |
| `discount_percent` outside 0–100 | Drop the row |
| `order_date` | Parse with `pd.to_datetime()` |

#### Transformation (`transform.py`)

| Step | Detail |
|---|---|
| Recalculate `final_price_usd` | `base_price_usd * (1 - discount_percent / 100)` |
| Recalculate `revenue_usd` | `final_price_usd * units_sold` |
| Add `year`, `month`, `day_of_week` | Extracted from `order_date` |
| Add `discount_amount` | `base_price_usd * (discount_percent / 100)` |
| Rename all columns | Snake_case → camelCase (e.g. `order_id` → `orderId`) |

> **Why camelCase?** The silver MySQL table schema uses camelCase column names. The conversion is done in `transform.py` before writing, so the column names match the table definition exactly.

---

### Task 4 — `load_to_postgres` (PythonOperator)

Copies the full silver dataset from MySQL across to PostgreSQL, staging it for the Spark KPI job.

- **Reads from:** `sports_footwear_sales_clean` (MySQL)
- **Writes to:** `sports_footwear_sales_staging` (PostgreSQL)
- **Strategy:** `if_exists='replace'` — drops and recreates the staging table on every run
- **Connections:** `mysql_staging`, `postgres_warehouse`

---

### Task 5 — `compute_gold_kpis` (SparkSubmitOperator)

Submits `spark_compute_kpis.py` as a Spark job. Spark reads the silver data directly from MySQL via JDBC and writes five KPI aggregations to the PostgreSQL `analytics` schema.

- **Reads from:** `sports_footwear_sales_clean` (MySQL, via JDBC)
- **Writes to:** `analytics.*` tables (PostgreSQL, via JDBC)
- **Connection:** `spark_default` (local mode)
- **JARs:** MySQL + PostgreSQL JDBC drivers

#### KPIs Computed

| Table | Group By | Metrics |
|---|---|---|
| `gold_brand_performance` | `brand` | Total revenue, total units, total orders, avg rating |
| `gold_monthly_sales` | `year`, `month` | Total revenue, total units, total orders |
| `gold_channel_performance` | `salesChannel` | Total revenue, total orders, avg units per order |
| `gold_country_performance` | `country` | Total revenue, total orders |
| `gold_overall_metrics` | — (single row) | Total revenue, total units, total orders, avg rating |

All tables are written with `mode("overwrite")` and `truncate=true`, so they're fully refreshed on every pipeline run.

---

## 6. Data Dictionary

### Source CSV — `global_sports_footwear_sales_2018_2026.csv`

| Column | Type | Description | Example |
|---|---|---|---|
| `order_id` | string | Unique order identifier | `ORD100000` |
| `order_date` | string (DD/MM/YYYY) | Date the order was placed | `30/01/2021` |
| `brand` | string | Sneaker brand | `Nike`, `Adidas`, `ASICS` |
| `model_name` | string | Product model name | `Model-370` |
| `category` | string | Product category | `Running`, `Lifestyle`, `Basketball`, `Training`, `Gym` |
| `gender` | string | Target gender | `Men`, `Women`, `Unisex` |
| `size` | integer | Shoe size | `8` |
| `color` | string | Shoe colour | `Black`, `White`, `Grey` |
| `base_price_usd` | integer | List price before discount | `162` |
| `discount_percent` | integer | Discount applied (0–30%) | `15` |
| `final_price_usd` | float | Price after discount | `137.70` |
| `units_sold` | integer | Number of units in order (1–4) | `1` |
| `revenue_usd` | float | `final_price_usd * units_sold` | `137.70` |
| `payment_method` | string | How the order was paid | `Card`, `Cash` |
| `sales_channel` | string | Where the sale occurred | `Retail Store`, `Online` |
| `country` | string | Country of sale | `USA`, `Germany`, `India`, `UK`, `UAE`, `Pakistan` |
| `customer_income_level` | string | Customer income bracket | `Low`, `Medium`, `High` |
| `customer_rating` | float | Customer satisfaction rating (3.0–5.0) | `4.6` |

---

### MySQL Bronze — `sports_footwear_sales_raw`

Mirrors the CSV schema exactly. All columns use snake_case. No primary key — intentionally raw.

| Column | MySQL Type |
|---|---|
| `order_id` | VARCHAR(255) |
| `order_date` | DATE |
| `brand` | VARCHAR(255) |
| `model_name` | VARCHAR(255) |
| `category` | VARCHAR(255) |
| `gender` | VARCHAR(50) |
| `size` | DECIMAL(5,2) |
| `color` | VARCHAR(50) |
| `base_price_usd` | DECIMAL(15,4) |
| `discount_percent` | DECIMAL(5,2) |
| `final_price_usd` | DECIMAL(15,4) |
| `units_sold` | INT |
| `revenue_usd` | DECIMAL(15,4) |
| `payment_method` | VARCHAR(50) |
| `sales_channel` | VARCHAR(50) |
| `country` | VARCHAR(100) |
| `customer_income_level` | VARCHAR(50) |
| `customer_rating` | DECIMAL(3,2) |
| `ingestion_timestamp` | TIMESTAMP |

---

### MySQL Silver — `sports_footwear_sales_clean`

Validated, transformed, camelCase columns. `orderId` is the primary key. Adds derived date and pricing columns.

| Column | MySQL Type | Notes |
|---|---|---|
| `orderId` | VARCHAR(255) PK | |
| `orderDate` | DATE | |
| `brand` | VARCHAR(255) | |
| `modelName` | VARCHAR(255) | |
| `category` | VARCHAR(255) | |
| `gender` | VARCHAR(50) | |
| `size` | DECIMAL(5,2) | |
| `color` | VARCHAR(50) | |
| `basePriceUsd` | DECIMAL(15,4) | |
| `discountPercent` | DECIMAL(5,2) | |
| `finalPriceUsd` | DECIMAL(15,4) | Recalculated in transform |
| `unitsSold` | INT | |
| `revenueUsd` | DECIMAL(15,4) | Recalculated in transform |
| `paymentMethod` | VARCHAR(50) | |
| `salesChannel` | VARCHAR(50) | |
| `country` | VARCHAR(100) | |
| `customerIncomeLevel` | VARCHAR(50) | |
| `customerRating` | DECIMAL(3,2) | |
| `year` | INT | Derived from `orderDate` |
| `month` | INT | Derived from `orderDate` |
| `dayOfWeek` | INT | 0=Monday, 6=Sunday |
| `discountAmount` | DECIMAL(15,4) | `basePriceUsd * discountPercent / 100` |

---

### PostgreSQL Gold — `analytics` schema

All tables are in the `analytics` schema and fully overwritten on every pipeline run.

**`gold_brand_performance`**

| Column | Type | Description |
|---|---|---|
| `brand` | VARCHAR(255) PK | |
| `total_revenue_usd` | DECIMAL(20,4) | |
| `total_units_sold` | BIGINT | |
| `total_orders` | BIGINT | |
| `avg_customer_rating` | DECIMAL(3,2) | |

**`gold_monthly_sales`**

| Column | Type | Description |
|---|---|---|
| `year` | INT PK | |
| `month` | INT PK | |
| `total_revenue_usd` | DECIMAL(20,4) | |
| `total_units_sold` | BIGINT | |
| `total_orders` | BIGINT | |

**`gold_channel_performance`**

| Column | Type | Description |
|---|---|---|
| `salesChannel` | VARCHAR(50) PK | |
| `total_revenue_usd` | DECIMAL(20,4) | |
| `total_orders` | BIGINT | |
| `avg_units_per_order` | DECIMAL(10,4) | |

**`gold_country_performance`**

| Column | Type | Description |
|---|---|---|
| `country` | VARCHAR(100) PK | |
| `total_revenue_usd` | DECIMAL(20,4) | |
| `total_orders` | BIGINT | |

**`gold_overall_metrics`**

| Column | Type | Description |
|---|---|---|
| `id` | INT PK DEFAULT 1 | Always 1 — single row table |
| `total_revenue_usd` | DECIMAL(20,4) | |
| `total_units_sold` | BIGINT | |
| `total_orders` | BIGINT | |
| `avg_customer_rating` | DECIMAL(3,2) | |
