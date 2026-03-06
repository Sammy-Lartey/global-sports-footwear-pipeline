# Stage 1: Get Spark
FROM apache/spark:3.5.1-python3 AS spark

# Stage 2: Build Airflow image
FROM apache/airflow:2.8.2-python3.11

USER root

# Copy Spark from the first stage
COPY --from=spark /opt/spark /opt/spark

# Set Spark and Java environment variables
ENV SPARK_HOME=/opt/spark
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$SPARK_HOME/bin:$JAVA_HOME/bin

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    default-libmysqlclient-dev \
    openjdk-17-jdk \
    procps \
    gcc \
    python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create directories for Spark jobs and data
RUN mkdir -p /opt/jobs /opt/airflow/data /opt/airflow/sql /opt/airflow/jars && \
    chown -R airflow:0 /opt/jobs /opt/airflow/data /opt/airflow/sql /opt/airflow/jars

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Switch to airflow user
USER airflow

# Upgrade pip first
RUN pip install --upgrade pip

# Install Python packages from requirements
RUN pip install --timeout=1200 --no-cache-dir -r /tmp/requirements.txt

# Install PySpark separately (version matching Spark)
RUN pip install --timeout=1200 --no-cache-dir pyspark==3.5.1

# Verify installations
RUN python -c "import pyspark; print(f' PySpark version: {pyspark.__version__}')" && \
    python -c "import airflow; print(' Airflow installed successfully')" && \
    python -c "import pandas; print(f' Pandas version: {pandas.__version__}')"