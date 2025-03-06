from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, explode
)
from datetime import datetime

NOW = datetime.now()

BUCKET = "wt-grepp-lake"
PLATFORM = "naver"
RAW = "s3a://{bucket}/raw/{platform}/{target}/{target_date}"


def get_comments(spark, date):
    url = RAW.format(bucket=BUCKET, platform=PLATFORM, target="comments", target_date=date)
    return spark.read.json(f"{url}/*/*.json", multiLine=True)


def get_episode_likes(spark, date):
    url = RAW.format(bucket=BUCKET, platform=PLATFORM, target="episode_likes", target_date=date)
    return spark.read.json(f"{url}/*/*.json", multiLine=True)


def get_episodes(spark, date):
    url = RAW.format(bucket=BUCKET, platform=PLATFORM, target="episodes", target_date=date)
    df = spark.read.json(f"{url}/*/*.json", multiLine=True)
    return df.select(
            explode(col("articleList")).alias("article"), 
            col("titleId").alias("title_id")
        )


def get_title_info(spark, date):
    url = RAW.format(bucket=BUCKET, platform=PLATFORM, target="title_info", target_date=date)
    return spark.read.json(f"{url}/*.json", multiLine=True)


def get_titles(spark, date, dayInt):
    days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

    url = RAW.format(bucket=BUCKET, platform=PLATFORM, target="titles", target_date=date)
    df = spark.read.json(f"{url}/*.json", multiLine=True)
    return df.select(
        explode(col(f"titleListMap.{days[dayInt]}")).alias("title"),
        lit(days[dayInt]).alias("weekday_str")
    )


def save_to_parquet(df, target):
    date_str = NOW.strftime("year=%Y/month=%m/day=%d")
    path = f"s3a://wt-grepp-lake/optimized/{target}/{date_str}/platform={PLATFORM}"
    df.coalesce(50).write.format("parquet").mode("append").save(path)
    print(f"Data successfully optimized to {path}")


def create_spark_session():
    return SparkSession.builder \
        .appName(f"S3 {PLATFORM} Data Optimizer") \
        .config("spark.hadoop.fs.s3a.endpoint", "s3.amazonaws.com") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()


def run():
    spark = create_spark_session()
    date_str = NOW.strftime("%Y/%m/%d")
    dayInt = NOW.weekday()

    titles_df = get_titles(spark, date_str, dayInt)
    save_to_parquet(titles_df, "titles")

    title_info_df = get_title_info(spark, date_str)
    save_to_parquet(title_info_df, "title_info")

    episodes_df = get_episodes(spark, date_str)
    save_to_parquet(episodes_df, "episodes")
    
    episode_likes_df = get_episode_likes(spark, date_str)
    save_to_parquet(episode_likes_df, "episode_likes")

    comments_df = get_comments(spark, date_str)
    save_to_parquet(comments_df, "comments")


run()
