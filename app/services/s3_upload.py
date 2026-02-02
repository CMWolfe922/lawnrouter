import boto3
import os
import uuid

s3 = boto3.client("s3")
BUCKET = os.getenv("BUCKET_NAME")


def generate_upload_url(company_id: str, filename: str):
    key = f"{company_id}/{uuid.uuid4()}_{filename}"

    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET,
            "Key": key,
            "ContentType": "image/jpeg"
        },
        ExpiresIn=3600
    )

    return {"upload_url": url, "key": key}
