import boto3
from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection

from example.python.common import config

service = 'aoss'
credentials = boto3.Session(profile_name="skku-opensearch-session").get_credentials()
auth = AWSV4SignerAuth(credentials, config.DEFAULT_REGION, service)


client = OpenSearch(
    hosts=[{'host': config.HOST, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300 # 대량 데이터 처리 시 timeout 시간 연장
)
