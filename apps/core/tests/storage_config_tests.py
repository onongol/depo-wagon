from storages.backends.s3boto3 import S3Boto3Storage

from config.settings import base


def _storage():
    return S3Boto3Storage(
        access_key="x",
        secret_key="x",
        bucket_name="b",
        endpoint_url="https://r2.example.com",
    )


class TestR2ClientConfig:
    def test_presigned_urls_are_signed_with_sigv4(self):
        # Without an explicit signature_version botocore presigns S3 with SigV2,
        # which R2 rejects, while the client config still reports s3v4.
        assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in _storage().url("a.jpg")

    def test_the_client_is_built_with_the_configured_timeouts_and_retries(self):
        config = _storage().connection.meta.client.meta.config
        expected = base.AWS_S3_CLIENT_CONFIG

        assert config.connect_timeout == expected.connect_timeout
        assert config.read_timeout == expected.read_timeout
        assert config.retries == expected.retries
