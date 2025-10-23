import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pyspark.sql.types import *

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)


def main():
    """Main function for Gold analytics job"""

    # Get job parameters
    args = getResolvedOptions(
        sys.argv, ["JOB_NAME", "SILVER_BUCKET", "GOLD_BUCKET", "DATABASE_NAME"]
    )

    job.init(args["JOB_NAME"], args)

    try:
        # Create user analytics
        create_user_analytics(
            silver_bucket=args["SILVER_BUCKET"],
            gold_bucket=args["GOLD_BUCKET"],
            database_name=args["DATABASE_NAME"],
        )

        # Create task analytics
        create_task_analytics(
            silver_bucket=args["SILVER_BUCKET"],
            gold_bucket=args["GOLD_BUCKET"],
            database_name=args["DATABASE_NAME"],
        )

        # Create business metrics
        create_business_metrics(
            silver_bucket=args["SILVER_BUCKET"],
            gold_bucket=args["GOLD_BUCKET"],
            database_name=args["DATABASE_NAME"],
        )

        job.commit()
        print("Gold analytics job completed successfully")

    except Exception as e:
        print(f"Gold analytics job failed: {e}")
        raise


def create_user_analytics(silver_bucket: str, gold_bucket: str, database_name: str):
    """Create user analytics and insights"""

    print("Creating user analytics...")

    # Read user data from Silver layer
    user_path = f"s3://{silver_bucket}/users/"
    user_df = spark.read.parquet(user_path)

    if user_df.count() == 0:
        print("No user data found in Silver layer")
        return

    # Simple user summary - just aggregate basic stats
    user_analytics = user_df.groupBy("user_id").agg(
        first("email").alias("email"),
        first("name").alias("name"),
        min("created_at").alias("first_seen"),
        max("updated_at").alias("last_updated"),
        sum("event_count").alias("total_events"),
        max("event_types").alias("max_event_types")
    )

    # Write user analytics to Gold layer
    gold_user_path = f"s3://{gold_bucket}/user_analytics/"
    user_analytics.write.mode("overwrite").parquet(gold_user_path)

    print(f"User analytics written to {gold_user_path}")


def create_task_analytics(silver_bucket: str, gold_bucket: str, database_name: str):
    """Create task analytics and insights"""

    print("Creating task analytics...")

    # Read task data from Silver layer
    task_path = f"s3://{silver_bucket}/tasks/"
    task_df = spark.read.parquet(task_path)

    if task_df.count() == 0:
        print("No task data found in Silver layer")
        return

    # Simple task summary
    task_analytics = task_df.groupBy("user_id").agg(
        count("*").alias("total_tasks"),
        count(when(col("status") == "completed", 1)).alias("completed_tasks"),
        count(when(col("status") == "pending", 1)).alias("pending_tasks"),
        count(when(col("status") == "in_progress", 1)).alias("in_progress_tasks"),
        min("created_at").alias("first_task_date"),
        max("updated_at").alias("last_task_date")
    )

    # Task trends by category
    category_trends = task_df.groupBy("category").agg(
        count("*").alias("total_tasks"),
        count(when(col("status") == "completed", 1)).alias("completed_tasks")
    )

    # Write task analytics to Gold layer
    gold_task_path = f"s3://{gold_bucket}/task_analytics/"
    task_analytics.write.mode("overwrite").parquet(f"{gold_task_path}user_metrics/")
    category_trends.write.mode("overwrite").parquet(f"{gold_task_path}category_trends/")

    print(f"Task analytics written to {gold_task_path}")


def create_business_metrics(silver_bucket: str, gold_bucket: str, database_name: str):
    """Create business metrics and KPIs"""

    print("Creating business metrics...")

    # Read data from Silver layer
    user_path = f"s3://{silver_bucket}/users/"
    task_path = f"s3://{silver_bucket}/tasks/"

    user_df = spark.read.parquet(user_path)
    task_df = spark.read.parquet(task_path)

    if user_df.count() == 0 and task_df.count() == 0:
        print("No data found in Silver layer")
        return

    # Simple business KPIs
    total_users = user_df.select("user_id").distinct().count()
    total_tasks = task_df.count()
    completed_tasks = task_df.filter(col("status") == "completed").count()

    business_kpis = spark.createDataFrame(
        [
            ("total_users", total_users),
            ("total_tasks", total_tasks),
            ("completed_tasks", completed_tasks),
        ],
        ["metric", "value"],
    )

    # Write business metrics to Gold layer
    gold_metrics_path = f"s3://{gold_bucket}/business_metrics/"
    business_kpis.write.mode("overwrite").parquet(f"{gold_metrics_path}kpis/")

    print(f"Business metrics written to {gold_metrics_path}")


if __name__ == "__main__":
    main()
