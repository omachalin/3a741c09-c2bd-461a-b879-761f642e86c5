from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class PrivateStorage(S3Boto3Storage):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME  # casino-private
    default_acl = None
    querystring_auth = True
    file_overwrite = False


class PublicStorage(S3Boto3Storage):
    bucket_name = settings.AWS_STATIC_BUCKET_NAME  # casino-public
    default_acl = 'public-read'
    querystring_auth = False
    file_overwrite = False
    custom_domain = False