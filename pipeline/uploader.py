import os
import boto3
from botocore.exceptions import ClientError


def upload_to_s3(mp3_bytes: bytes, arxiv_id: str) -> str:
    """
    Upload an MP3 file to S3 and return a presigned URL valid for 7 days.

    Required env vars:
        AWS_ACCESS_KEY_ID
        AWS_SECRET_ACCESS_KEY
        AWS_REGION          (e.g. ap-south-1)
        S3_BUCKET_NAME

    Returns:
        Presigned URL string
    """
    bucket = os.environ["S3_BUCKET_NAME"]
    region = os.environ.get("AWS_REGION", "ap-south-1")
    key = f"podcasts/{arxiv_id}.mp3"

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

    # Upload
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=mp3_bytes,
        ContentType="audio/mpeg",
    )

    # Generate presigned URL (7 days)
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=604800,
    )

    return url


def get_existing_url(arxiv_id: str) -> str | None:
    """
    Check if a podcast already exists in S3 for this arxiv_id.
    Returns presigned URL if found, else None.
    """
    bucket = os.environ["S3_BUCKET_NAME"]
    region = os.environ.get("AWS_REGION", "ap-south-1")
    key = f"podcasts/{arxiv_id}.mp3"

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

    try:
        s3.head_object(Bucket=bucket, Key=key)
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=604800,
        )
        return url
    except ClientError:
        return None
