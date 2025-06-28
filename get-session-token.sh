#!/bin/bash

# 원본 프로파일 이름 (IAM 사용자용)
SOURCE_PROFILE="skku-opensearch"

# 새로 저장할 프로파일 이름
TARGET_PROFILE="skku-opensearch-session"

# STS 임시 자격 증명 발급
CREDS=$(aws sts get-session-token \
    --duration-seconds 3600 \
    --profile "$SOURCE_PROFILE" \
    --output json)

if [ $? -ne 0 ]; then
  echo "❌ STS 세션 토큰 요청 실패"
  exit 1
fi

# 필드 추출
AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.Credentials.AccessKeyId')
AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.Credentials.SecretAccessKey')
AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.Credentials.SessionToken')
EXPIRATION=$(echo "$CREDS" | jq -r '.Credentials.Expiration')

# 새 프로파일로 설정
aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" --profile "$TARGET_PROFILE"
aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" --profile "$TARGET_PROFILE"
aws configure set aws_session_token "$AWS_SESSION_TOKEN" --profile "$TARGET_PROFILE"

echo "✅ 세션 토큰이 [$TARGET_PROFILE] 프로파일로 저장되었습니다"
echo "⏳ 만료 시간(UTC): $EXPIRATION"
