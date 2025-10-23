import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
from datetime import datetime

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

def main():
    """Main function for Silver transformation job"""
    
    # Get job parameters
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'BRONZE_BUCKET',
        'SILVER_BUCKET',
        'DATABASE_NAME'
    ])
    
    job.init(args['JOB_NAME'], args)
    
    try:
        # Process CDC events from Bronze layer
        process_cdc_events(
            bronze_bucket=args['BRONZE_BUCKET'],
            silver_bucket=args['SILVER_BUCKET'],
            database_name=args['DATABASE_NAME']
        )
        
        # Process user data
        process_user_data(
            bronze_bucket=args['BRONZE_BUCKET'],
            silver_bucket=args['SILVER_BUCKET'],
            database_name=args['DATABASE_NAME']
        )
        
        # Process task data
        process_task_data(
            bronze_bucket=args['BRONZE_BUCKET'],
            silver_bucket=args['SILVER_BUCKET'],
            database_name=args['DATABASE_NAME']
        )
        
        job.commit()
        print("Silver transformation job completed successfully")
        
    except Exception as e:
        print(f"Silver transformation job failed: {e}")
        raise

def process_cdc_events(bronze_bucket: str, silver_bucket: str, database_name: str):
    """Process CDC events and create aggregated views"""
    
    print("Processing CDC events...")
    
    # Read CDC events from Bronze layer
    cdc_path = f"s3://{bronze_bucket}/cdc/"
    cdc_df = spark.read.json(cdc_path)
    
    if cdc_df.count() == 0:
        print("No CDC events found in Bronze layer")
        return
    
    # Filter CDC events first
    cdc_filtered = cdc_df.filter(
        col("event_name").isin(["INSERT", "MODIFY"])
    )

    # Add entity_type column
    cdc_with_entity_type = cdc_filtered.withColumn(
        "entity_type",
        when(col("data.PK").startswith("USER#"), "USER")
        .when(col("data.PK").startswith("TASK#"), "TASK")
        .when(col("data.PK").startswith("IDEMPOTENCY#"), "IDEMPOTENCY")
        .otherwise("UNKNOWN")
    )

    # Now select all fields including derived user_id and task_id
    cdc_processed = cdc_with_entity_type.select(
        col("event_name"),
        col("event_time"),
        col("sequence_number"),
        col("table_name"),
        col("processed_at"),
        col("partition_key"),
        col("data.PK").alias("primary_key"),
        col("data.SK").alias("sort_key"),
        col("data.GSI1PK").alias("gsi1_pk"),
        col("data.GSI1SK").alias("gsi1_sk"),
        col("data.GSI2PK").alias("gsi2_pk"),
        col("data.GSI2SK").alias("gsi2_sk"),
        col("data.GSI3PK").alias("gsi3_pk"),
        col("data.GSI3SK").alias("gsi3_sk"),
        col("data.GSI4PK").alias("gsi4_pk"),
        col("data.GSI4SK").alias("gsi4_sk"),
        col("entity_type"),
        when(col("entity_type") == "USER", regexp_replace(col("data.PK"), "USER#", ""))
         .when(col("entity_type") == "TASK", regexp_replace(col("data.PK"), "TASK#", ""))
         .otherwise(None).alias("user_id"),
        when(col("entity_type") == "TASK", regexp_replace(col("data.SK"), "TASK#", ""))
         .otherwise(None).alias("task_id"),
        col("data.title").alias("title"),
        col("data.description").alias("description"),
        col("data.status").alias("status"),
        col("data.priority").alias("priority"),
        col("data.category").alias("category"),
        col("data.created_at").alias("created_at"),
        col("data.updated_at").alias("updated_at"),
        col("data.email").alias("email"),
        col("data.name").alias("name")
    )
    
    # Add partitioning columns
    cdc_processed = cdc_processed.withColumn(
        "year", year(col("processed_at").cast("date"))
    ).withColumn(
        "month", month(col("processed_at").cast("date"))
    ).withColumn(
        "day", dayofmonth(col("processed_at").cast("date"))
    )
    
    # Write to Silver layer
    silver_cdc_path = f"s3://{silver_bucket}/cdc/"
    cdc_processed.write \
        .mode("append") \
        .partitionBy("year", "month", "day") \
        .parquet(silver_cdc_path)
    
    print(f"CDC events processed and written to {silver_cdc_path}")

def process_user_data(bronze_bucket: str, silver_bucket: str, database_name: str):
    """Process user data and create user analytics views"""
    
    print("Processing user data...")
    
    # Read user data from Bronze layer
    user_path = f"s3://{bronze_bucket}/cdc/"
    user_df = spark.read.json(user_path)

    if user_df.count() == 0:
        print("No user data found in Bronze layer")
        return

    # Add entity_type column and filter for user entities
    user_df_with_type = user_df.withColumn(
        "entity_type",
        when(col("data.PK").startswith("USER#"), "USER")
        .when(col("data.PK").startswith("TASK#"), "TASK")
        .when(col("data.PK").startswith("IDEMPOTENCY#"), "IDEMPOTENCY")
        .otherwise("UNKNOWN")
    )

    user_data = user_df_with_type.filter(
        col("entity_type") == "USER"
    ).select(
        regexp_replace(col("data.PK"), "USER#", "").alias("user_id"),
        col("data.email").alias("email"),
        col("data.name").alias("name"),
        col("data.created_at").alias("created_at"),
        col("data.updated_at").alias("updated_at"),
        col("processed_at").alias("processed_at"),
        col("event_name").alias("event_name")
    )
    
    # Create user analytics aggregations
    user_analytics = user_data.groupBy("user_id").agg(
        first("email").alias("email"),
        first("name").alias("name"),
        min("created_at").alias("created_at"),
        max("updated_at").alias("updated_at"),
        count("*").alias("event_count"),
        countDistinct("event_name").alias("event_types")
    )
    
    # Add partitioning columns (convert timestamp to date first)
    user_analytics = user_analytics.withColumn(
        "created_date", from_unixtime(col("created_at")).cast("date")
    ).withColumn(
        "year", year(col("created_date"))
    ).withColumn(
        "month", month(col("created_date"))
    ).withColumn(
        "day", dayofmonth(col("created_date"))
    )
    
    # Write to Silver layer
    silver_user_path = f"s3://{silver_bucket}/users/"
    user_analytics.write \
        .mode("append") \
        .partitionBy("year", "month", "day") \
        .parquet(silver_user_path)
    
    print(f"User data processed and written to {silver_user_path}")

def process_task_data(bronze_bucket: str, silver_bucket: str, database_name: str):
    """Process task data and create task analytics views"""
    
    print("Processing task data...")
    
    # Read task data from Bronze layer
    task_path = f"s3://{bronze_bucket}/cdc/"
    task_df = spark.read.json(task_path)

    if task_df.count() == 0:
        print("No task data found in Bronze layer")
        return

    # Add entity_type column and filter for task entities
    task_df_with_type = task_df.withColumn(
        "entity_type",
        when(col("data.PK").startswith("USER#"), "USER")
        .when(col("data.PK").startswith("TASK#"), "TASK")
        .when(col("data.PK").startswith("IDEMPOTENCY#"), "IDEMPOTENCY")
        .otherwise("UNKNOWN")
    )

    task_data = task_df_with_type.filter(
        col("entity_type") == "TASK"
    ).select(
        regexp_replace(col("data.SK"), "TASK#", "").alias("task_id"),
        regexp_replace(col("data.PK"), "TASK#", "").alias("user_id"),
        col("data.title").alias("title"),
        col("data.description").alias("description"),
        col("data.status").alias("status"),
        col("data.priority").alias("priority"),
        col("data.category").alias("category"),
        col("data.created_at").alias("created_at"),
        col("data.updated_at").alias("updated_at"),
        col("processed_at").alias("processed_at"),
        col("event_name").alias("event_name")
    )
    
    # Create task analytics aggregations
    task_analytics = task_data.groupBy("task_id").agg(
        first("user_id").alias("user_id"),
        first("title").alias("title"),
        first("description").alias("description"),
        first("status").alias("status"),
        first("priority").alias("priority"),
        first("category").alias("category"),
        min("created_at").alias("created_at"),
        max("updated_at").alias("updated_at"),
        count("*").alias("event_count"),
        countDistinct("event_name").alias("event_types")
    )
    
    # Add partitioning columns (convert timestamp to date first)
    task_analytics = task_analytics.withColumn(
        "created_date", from_unixtime(col("created_at")).cast("date")
    ).withColumn(
        "year", year(col("created_date"))
    ).withColumn(
        "month", month(col("created_date"))
    ).withColumn(
        "day", dayofmonth(col("created_date"))
    )
    
    # Write to Silver layer
    silver_task_path = f"s3://{silver_bucket}/tasks/"
    task_analytics.write \
        .mode("append") \
        .partitionBy("year", "month", "day") \
        .parquet(silver_task_path)
    
    print(f"Task data processed and written to {silver_task_path}")

if __name__ == "__main__":
    main()
