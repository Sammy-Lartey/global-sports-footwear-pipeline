from pyspark.sql.functions import lit
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum, count, avg
import os


print("Starting Spark KPI Computation")


# Get database credentials from environment
mysql_host = os.getenv('MYSQL_STAGING_HOST')
mysql_port = os.getenv('MYSQL_STAGING_PORT')
mysql_db = os.getenv('MYSQL_STAGING_DATABASE')
mysql_user = os.getenv('MYSQL_STAGING_USER')
mysql_pass = os.getenv('MYSQL_STAGING_PASSWORD')

postgres_host = os.getenv('POSTGRES_WAREHOUSE_HOST')
postgres_port = os.getenv('POSTGRES_WAREHOUSE_PORT')
postgres_db = os.getenv('POSTGRES_WAREHOUSE_DATABASE')
postgres_user = os.getenv('POSTGRES_WAREHOUSE_USER')
postgres_pass = os.getenv('POSTGRES_WAREHOUSE_PASSWORD')

# Create Spark session
spark = SparkSession.builder \
    .appName("SneakerSalesKPIs") \
    .config("spark.jars", os.getenv('SPARK_JARS', '')) \
    .getOrCreate()

print("Spark session created")

# READ DATA 
print("Reading silver data from MySQL...")

silver_df = spark.read \
    .format("jdbc") \
    .option("url", f"jdbc:mysql://{mysql_host}:{mysql_port}/{mysql_db}") \
    .option("dbtable", "sports_footwear_sales_clean") \
    .option("user", mysql_user) \
    .option("password", mysql_pass) \
    .option("driver", "com.mysql.cj.jdbc.Driver") \
    .load()

row_count = silver_df.count()
print(f"Read {row_count} rows from silver layer")


# COMPUTE KPIS

# 1. Brand performance
print("Computing brand KPIs...")
brand_kpis = silver_df.groupBy("brand").agg(
    spark_sum("revenueUsd").alias("total_revenue_usd"),
    spark_sum("unitsSold").alias("total_units_sold"),
    count("orderId").alias("total_orders"),
    avg("customerRating").alias("avg_customer_rating")
)

# 2. Monthly sales
print("Computing monthly KPIs...")
# year and month already exist in silver layer (added by transform.py)
monthly_kpis = silver_df.groupBy("year", "month").agg(
    spark_sum("revenueUsd").alias("total_revenue_usd"),
    spark_sum("unitsSold").alias("total_units_sold"),
    count("orderId").alias("total_orders")
).orderBy("year", "month")

# 3. Channel performance
print("Computing channel KPIs...")
channel_kpis = silver_df.groupBy("salesChannel").agg(
    spark_sum("revenueUsd").alias("total_revenue_usd"),
    count("orderId").alias("total_orders"),
    avg("unitsSold").alias("avg_units_per_order")
)

# 4. Country performance
print("Computing country KPIs...")
country_kpis = silver_df.groupBy("country").agg(
    spark_sum("revenueUsd").alias("total_revenue_usd"),
    count("orderId").alias("total_orders")
).orderBy(col("total_revenue_usd").desc())

# 5. Overall metrics
print("Computing overall metrics...")
overall = silver_df.agg(
    spark_sum("revenueUsd").alias("total_revenue_usd"),
    spark_sum("unitsSold").alias("total_units_sold"),
    count("orderId").alias("total_orders"),
    avg("customerRating").alias("avg_customer_rating")
)
overall = overall.withColumn("id", lit(1))

# Write to postgres
print("Writing KPIs to PostgreSQL...")

def write_to_postgres(df, table_name):
    try:
        row_count = df.count()

        df.write \
            .format("jdbc") \
            .option("url", f"jdbc:postgresql://{postgres_host}:{postgres_port}/{postgres_db}") \
            .option("dbtable", f"analytics.{table_name}") \
            .option("user", postgres_user) \
            .option("password", postgres_pass) \
            .option("driver", "org.postgresql.Driver") \
            .option("truncate", "true") \
            .mode("overwrite") \
            .save()
        print(f"Wrote {row_count} rows to {table_name}")

    except Exception as e:
        print(f"Error writing to {table_name}: {e}")
        raise


# Write each KPI
write_to_postgres(brand_kpis, "gold_brand_performance")
write_to_postgres(monthly_kpis, "gold_monthly_sales")
write_to_postgres(channel_kpis, "gold_channel_performance")
write_to_postgres(country_kpis, "gold_country_performance")
write_to_postgres(overall, "gold_overall_metrics")


print("Spark KPI computation complete!")


spark.stop()