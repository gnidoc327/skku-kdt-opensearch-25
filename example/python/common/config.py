import os

# ==============================================================================
# --- 설정 (Configuration) ---
# 아래 값들을 사용자의 환경에 맞게 수정해주세요.
# ==============================================================================

# TODO: 아래 값을 입력해주세요.
# 1. OpenSearch Serverless 엔드포인트
# Terraform output에서 'collection_endpoint' 값을 복사하여
# 'https://'를 제외하고 입력
# 예: 'xxxxxxxxxxxx.ap-northeast-2.aoss.amazonaws.com'
HOST = os.environ.get("OPENSEARCH_HOST", "1qe63zy9hn7mb2ekljid.ap-northeast-2.aoss.amazonaws.com")

# 2. AWS 리전
DEFAULT_REGION = "ap-northeast-2"
BEDROCK_REGION = "us-east-1"

# 3. 사용할 AWS 프로필 이름
# 환경 변수가 없으면 'default' 프로필을 사용합니다.
PROFILE = os.environ.get("AWS_PROFILE", "skku-opensearch-session")
