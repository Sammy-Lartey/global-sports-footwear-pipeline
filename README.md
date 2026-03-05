# Global Sports Footwear Sales Pipeline

End-to-end ETL pipeline using Apache Airflow to process and analyze global sports footwear sales data. The pipeline ingests raw CSV data, validates and transforms it through a Bronze/Silver/Gold medallion architecture, computes key performance indicators using Apache Spark, and stores the final results in a PostgreSQL data warehouse for further analysis.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Apache Airflow 2.8.1 | Orchestration |
| Apache Spark 3.5.1 | KPI computation |
| MySQL 8.0 | Bronze + Silver layers |
| PostgreSQL 16 | Gold layer / data warehouse |
| Docker | Containerisation |
| pandas / SQLAlchemy | Data ingestion + transformation |

---

## Prerequisites

- Docker Desktop (WSL2 backend on Windows)
- At least 6GB RAM allocated to Docker
- JDBC JAR files in `./jars/`:
  - [`mysql-connector-j-9.6.0.jar`](https://mvnrepository.com/artifact/com.mysql/mysql-connector-j/9.6.0)
  - [`postgresql-42.7.9.jar`](https://mvnrepository.com/artifact/org.postgresql/postgresql/42.7.9)
- Source CSV in `./data/` — `global_sports_footwear_sales_2018_2026.csv`

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/Sammy-Lartey/global-sports-footwear-pipeline.git
cd global-sports-footwear-pipeline

# 2. Set up environment variables
cp .env.example .env
# Fill in your credentials in .env

# 3. Build the custom Airflow + Spark image
docker compose build

# 4. Initialise Airflow (run once)
docker compose up airflow-init

# 5. Start all services
docker compose up
```

Then go to `http://localhost:8080`, log in with your credentials, unpause the `sneaker_sales_pipeline` DAG and trigger it.

---

## Project Structure

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
├── data/                               # Place source CSV here
├── jars/                               # Place JDBC JARs here
│
├── sql/
│   ├── init_staging.sql                # MySQL schema (Bronze + Silver)
│   └── init_analytics.sql             # PostgreSQL schema (Gold)
│
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Pipeline Overview

```
CSV File
   │
   ▼  FileSensor
┌──────────────────────────────┐
│  BRONZE  (MySQL)             │  Raw ingestion — no transforms
└──────────────────────────────┘
   │
   ▼  validate + transform
┌──────────────────────────────┐
│  SILVER  (MySQL)             │  Cleaned, typed, camelCase columns
└──────────────────────────────┘
   │
   ▼  copy to warehouse
┌──────────────────────────────┐
│  GOLD  (PostgreSQL)          │  KPI aggregations via Spark
└──────────────────────────────┘
```

Five tasks run sequentially:

```
wait_for_csv >> ingest_csv_to_mysql >> validate_and_transform_data >> load_to_postgres >> compute_gold_kpis
```

---

## Useful Commands

```bash
# Stop all services
docker compose down

# Full reset (wipes all DB volumes)
docker compose down -v

# Rebuild image after code changes
docker compose build --no-cache
```

---

## Documentation

For a full breakdown of the pipeline, data dictionary, schema definitions, and architecture details see [`documentation.md`](documentation.md).
