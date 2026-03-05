from pathlib import Path
import os

DATA_PATH = Path(os.getenv("DATA_DIR", "/opt/airflow/data"))
JARS_PATH = Path(os.getenv("JARS_DIR", "/opt/airflow/jars"))
SQL_PATH = Path(os.getenv("SQL_DIR", "/opt/airflow/sql"))