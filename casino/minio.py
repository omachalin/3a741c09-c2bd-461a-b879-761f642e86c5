from django.conf import settings
import boto3
from botocore.client import Config

class MinioService:
    def __init__(self, use_public=False):
        self.bucket = settings.MINIO_PUBLIC_BUCKETS[0] if use_public else settings.MINIO_PRIVATE_BUCKETS[0]
        self.client = boto3.client(
            's3',
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )

    def generate_presigned_url(self, key, expiry=None):
        expiry = int(settings.MINIO_URL_EXPIRY_HOURS.total_seconds()) if expiry is None else expiry
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expiry
        )

    def upload_file(self, file_obj, key):
        self.client.upload_fileobj(file_obj, self.bucket, key)

    def delete_file(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)
