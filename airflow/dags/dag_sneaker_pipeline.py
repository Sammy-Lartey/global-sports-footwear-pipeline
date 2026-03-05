from pathlib import Path
from airflow import DAG
from airflow.sensors.filesystem import FileSensor # pyright: ignore[reportMissingImports]
from airflow.operators.python import PythonOperator # pyright: ignore[reportMissingImports]
from airflow.providers.mysql.hooks.mysql import MySqlHook # pyright: ignore[reportMissingImports]
from airflow.providers.postgres.hooks.postgres import PostgresHook # pyright: ignore[reportMissingImports]
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime, timedelta
import pandas as pd
import os
from sqlalchemy import text

from scripts.config import DATA_PATH, JARS_PATH 
from scripts.validate import validate_data
from scripts.transform import transform_data

# Default arguments
default_args = {
    'owner': 'AspiringHippie',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


# TASK FUNCTIONS

def ingest_csv_to_mysql(**kwargs):

    # Read CSV and load into MySQL (Bronze layer)
    mysql_hook = MySqlHook(mysql_conn_id='mysql_staging')
    csv_path = DATA_PATH / 'global_sports_footwear_sales_2018_2026.csv'
    
    print(f"Reading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Read {len(df)} rows from CSV")
    
    engine = mysql_hook.get_sqlalchemy_engine()
    
    # Truncate and load
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE sports_footwear_sales_raw"))
        conn.commit()
    
    df.to_sql('sports_footwear_sales_raw', con=engine, if_exists='append', index=False)
    print(f"Loaded {len(df)} rows to MySQL bronze table")


def validate_and_transform_data(**kwargs):
    
    # Read from MySQL, validate, transform, and write back (Silver layer)
    mysql_hook = MySqlHook(mysql_conn_id='mysql_staging')
    engine = mysql_hook.get_sqlalchemy_engine()
    
    # Read from bronze
    print("Reading from bronze table...")
    df = pd.read_sql("SELECT * FROM sports_footwear_sales_raw", con=engine)
    print(f"Read {len(df)} rows")
    
    # Validate
    print("Validating data...")
    df_validated = validate_data(df)
    
    # Transform
    print("Transforming data...")
    df_silver = transform_data(df_validated)
    
    # Write to silver table
    mysql_hook.run("TRUNCATE TABLE sports_footwear_sales_clean")
    df_silver.to_sql('sports_footwear_sales_clean', con=engine, if_exists='append', index=False)
    print(f"Wrote {len(df_silver)} rows to silver table")


def load_to_postgres(**kwargs):

    # Load silver data from MySQL to PostgreSQL (Gold layer staging)
    mysql_hook = MySqlHook(mysql_conn_id='mysql_staging')
    postgres_hook = PostgresHook(postgres_conn_id='postgres_warehouse')
    
    # Read from MySQL silver
    mysql_engine = mysql_hook.get_sqlalchemy_engine()
    df = pd.read_sql("SELECT * FROM sports_footwear_sales_clean", con=mysql_engine)
    
    # Write to PostgreSQL
    postgres_engine = postgres_hook.get_sqlalchemy_engine()
    df.to_sql('sports_footwear_sales_staging', con=postgres_engine, if_exists='replace', index=False)
    print(f"Loaded {len(df)} rows to PostgreSQL staging")



# DAG DEFINITION
with DAG(
    'sneaker_sales_pipeline',
    default_args=default_args,
    description='Sneaker sales ETL pipeline',
    schedule_interval='@daily',
    catchup=False,
) as dag:

    # Task 1: Wait for CSV file
    wait_for_csv = FileSensor(
        task_id='wait_for_csv',
        filepath=str(DATA_PATH / 'global_sports_footwear_sales_2018_2026.csv'),
        poke_interval=30,
        timeout=600
    )

    # Task 2: Ingest to MySQL
    ingest_data = PythonOperator(
        task_id='ingest_csv_to_mysql',
        python_callable=ingest_csv_to_mysql
    )

    # Task 3: Validate and transform
    validate_transform = PythonOperator(
        task_id='validate_and_transform_data',
        python_callable=validate_and_transform_data
    )

    # Task 4: Load to PostgreSQL
    load_postgres = PythonOperator(
        task_id='load_to_postgres',
        python_callable=load_to_postgres
    )

    # Task 5: Compute KPIs with Spark
    jars = f"{JARS_PATH / 'mysql-connector-j-9.6.0.jar'},{JARS_PATH / 'postgresql-42.7.9.jar'}"
    
    compute_kpis = SparkSubmitOperator(
        task_id='compute_gold_kpis',
        application=str(Path(__file__).parent / 'spark_compute_kpis.py'),
        conn_id='spark_default',
        verbose=True,
        jars=jars,
        conf={
            'spark.executor.memory': '2g',
            'spark.driver.memory': '2g'
        }
    )

    # Set task dependencies
    wait_for_csv >> ingest_data >> validate_transform >> load_postgres >> compute_kpis