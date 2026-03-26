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
| `mysql` | mysql:8.0 | Bronze + Silver layers | 3307 |
| `warehouse` | postgres:16 | Gold layer / analytics | 5433 |

### Custom Airflow Image

The stock Airflow image doesn't include Java or Spark. The `Dockerfile` does a two-stage build:
- **Stage 1:** Pulls Spark 3.5.1 from `apache/spark:3.5.1-python3`
- **Stage 2:** Copies Spark into the Airflow 3.1.8 image, installs OpenJDK 17, and installs Python dependencies

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

> **Note:** `scripts/` lives inside `airflow/dags/` so that the single volume mount `./airflow/dags:/opt/airflow/dags` covers the DAG, the Spark script, and the scripts package all at once.

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

```bash
cp .env.example .env
```

### Step 3 — Build the custom image

```bash
docker compose build
```

### Step 4 — Initialise Airflow

```bash
docker compose up airflow-init
```

Wait for `Database migrating done!` before proceeding.

### Step 5 — Start all services

```bash
docker compose up -d
```

### Step 6 — Get the admin password

Airflow 3.x auto-generates an admin password on first start. Retrieve it with:

```bash
docker compose logs airflow-apiserver | findstr "Password"
```

Go to `http://localhost:8080` and log in with username `admin` and the generated password.

### Step 7 — Create the fs_default connection

Before running the pipeline, create the filesystem connection in the Airflow UI:

1. Go to **Admin → Connections**
2. Click **+**
3. Fill in:
   - **Connection Id:** `fs_default`
   - **Connection Type:** `File(path)`
   - **Path:** `/`
4. Click **Save**

### Step 8 — Run the pipeline

1. Find the `sneaker_sales_pipeline` DAG
2. Toggle it from paused to active
3. Click **Trigger DAG**

### Stopping everything

```bash
docker compose down       # stop containers
docker compose down -v    # full reset including DB volumes
```

---

## 5. Pipeline Walkthrough

The DAG is defined in `dag_sneaker_pipeline.py` and is set to manual trigger (`schedule=None`). Five tasks run sequentially:

```
wait_for_csv >> ingest_csv_to_mysql >> validate_and_transform_data >> load_to_postgres >> compute_gold_kpis
```

---

### Task 1 — `wait_for_csv` (FileSensor)

Polls for the CSV file every 30 seconds, timing out after 10 minutes.

- **Operator:** `airflow.providers.standard.sensors.filesystem.FileSensor`
- **Polls:** `/opt/airflow/data/global_sports_footwear_sales_2018_2026.csv`
- **Requires:** `fs_default` connection

---

### Task 2 — `ingest_csv_to_mysql` (PythonOperator)

Reads the raw CSV and loads it into the MySQL bronze table with no transformations.

- **Reads from:** CSV file via pandas
- **Writes to:** `sports_footwear_sales_raw` (MySQL)
- **Strategy:** Truncate then append (idempotent)
- **Note:** Parses `DD/MM/YYYY` dates to `YYYY-MM-DD` before loading

---

### Task 3 — `validate_and_transform_data` (PythonOperator)

Validates and transforms the bronze data, writes the clean result to the silver table.

- **Reads from:** `sports_footwear_sales_raw` (MySQL)
- **Writes to:** `sports_footwear_sales_clean` (MySQL)

#### Validation (`validate.py`)

| Check | Action |
|---|---|
| Duplicate `order_id` | Drop duplicates, keep first |
| Missing `order_id`, `brand`, or `units_sold` | Drop the row |
| Non-numeric values in numeric columns | Coerce, drop rows where critical columns are NaN |
| `discount_percent` outside 0–100 | Drop the row |

#### Transformation (`transform.py`)

| Step | Detail |
|---|---|
| Recalculate `final_price_usd` | `base_price_usd * (1 - discount_percent / 100)` |
| Recalculate `revenue_usd` | `final_price_usd * units_sold` |
| Add `year` | Integer year extracted from `order_date` |
| Add `month` | Full month name e.g. `January` |
| Add `day_of_week` | Full day name e.g. `Monday` |
| Add `discount_amount` | `base_price_usd * (discount_percent / 100)` |
| Rename all columns | snake_case → camelCase |

---

### Task 4 — `load_to_postgres` (PythonOperator)

Copies the full silver dataset from MySQL to PostgreSQL staging.

- **Reads from:** `sports_footwear_sales_clean` (MySQL)
- **Writes to:** `sports_footwear_sales_staging` (PostgreSQL)
- **Strategy:** `if_exists='replace'`

---

### Task 5 — `compute_gold_kpis` (SparkSubmitOperator)

Submits `spark_compute_kpis.py` as a Spark job that reads from MySQL via JDBC and writes five KPI tables to PostgreSQL.

#### KPIs Computed

| Table | Group By | Metrics |
|---|---|---|
| `gold_brand_performance` | `brand` | Total revenue, units, orders, avg rating |
| `gold_monthly_sales` | `year`, `month` | Total revenue, units, orders |
| `gold_channel_performance` | `salesChannel` | Total revenue, orders, avg units per order |
| `gold_country_performance` | `country` | Total revenue, orders |
| `gold_overall_metrics` | — (single row) | Total revenue, units, orders, avg rating |

---

## 6. Data Dictionary

### Source CSV

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Unique order identifier |
| `order_date` | string (DD/MM/YYYY) | Date the order was placed |
| `brand` | string | Sneaker brand |
| `model_name` | string | Product model name |
| `category` | string | Running, Lifestyle, Basketball, Training, Gym |
| `gender` | string | Men, Women, Unisex |
| `size` | integer | Shoe size |
| `color` | string | Shoe colour |
| `base_price_usd` | integer | List price before discount |
| `discount_percent` | integer | Discount applied (0–30%) |
| `final_price_usd` | float | Price after discount |
| `units_sold` | integer | Units in order (1–4) |
| `revenue_usd` | float | `final_price_usd * units_sold` |
| `payment_method` | string | Card, Cash, Wallet, Bank Transfer |
| `sales_channel` | string | Retail Store, Online |
| `country` | string | USA, Germany, India, UK, UAE, Pakistan |
| `customer_income_level` | string | Low, Medium, High |
| `customer_rating` | float | Rating 3.0–5.0 |

### MySQL Silver — `sports_footwear_sales_clean`

| Column | Type | Notes |
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
| `finalPriceUsd` | DECIMAL(15,4) | Recalculated |
| `unitsSold` | INT | |
| `revenueUsd` | DECIMAL(15,4) | Recalculated |
| `paymentMethod` | VARCHAR(50) | |
| `salesChannel` | VARCHAR(50) | |
| `country` | VARCHAR(100) | |
| `customerIncomeLevel` | VARCHAR(50) | |
| `customerRating` | DECIMAL(3,2) | |
| `year` | INT | |
| `month` | VARCHAR(20) | e.g. January |
| `dayOfWeek` | VARCHAR(20) | e.g. Monday |
| `discountAmount` | DECIMAL(15,4) | |

### PostgreSQL Gold — `analytics` schema

All tables fully overwritten on every pipeline run.

**`gold_brand_performance`** — grouped by `brand`
**`gold_monthly_sales`** — grouped by `year`, `month`
**`gold_channel_performance`** — grouped by `salesChannel`
**`gold_country_performance`** — grouped by `country`
**`gold_overall_metrics`** — single row summary