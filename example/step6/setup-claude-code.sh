#!/bin/bash
# =============================================================================
# Step 6. Claude Code + Amazon Bedrock 환경 설정 스크립트
#
# 사용법: source example/step6/setup-claude-code.sh
# =============================================================================

# --- 1. AWS 세션 토큰 확인 ---
PROFILE="skku-opensearch-session"

echo "🔍 AWS 프로파일 [$PROFILE] 확인 중..."
if aws sts get-caller-identity --profile "$PROFILE" > /dev/null 2>&1; then
    ACCOUNT=$(aws sts get-caller-identity --profile "$PROFILE" --query 'Account' --output text)
    echo "✅ AWS 인증 확인 완료 (Account: $ACCOUNT)"
else
    echo "❌ AWS 세션 토큰이 만료되었거나 프로파일이 없습니다."
    echo "   먼저 실행하세요: ./get-session-token.sh"
    return 1 2>/dev/null || exit 1
fi

# --- 2. Bedrock 모델 접근 확인 ---
echo ""
echo "🔍 Bedrock 모델 접근 권한 확인 중..."
if aws bedrock list-inference-profiles \
    --profile "$PROFILE" \
    --region us-east-1 \
    --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `anthropic.claude`)].inferenceProfileId' \
    --output text > /dev/null 2>&1; then
    echo "✅ Bedrock 접근 가능"
else
    echo "⚠️  Bedrock 접근을 확인할 수 없습니다. 모델 활성화가 필요할 수 있습니다."
    echo "   → https://console.aws.amazon.com/bedrock/ 에서 모델 접근 권한을 확인하세요."
fi

# --- 3. 환경 변수 설정 ---
echo ""
echo "⚙️  환경 변수 설정 중..."

export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1
export AWS_PROFILE="$PROFILE"
export ANTHROPIC_MODEL="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
export ANTHROPIC_SMALL_FAST_MODEL="us.anthropic.claude-haiku-4-5-20251001-v1:0"

echo "   CLAUDE_CODE_USE_BEDROCK=1"
echo "   AWS_REGION=us-east-1"
echo "   AWS_PROFILE=$PROFILE"
echo "   ANTHROPIC_MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0"
echo "   ANTHROPIC_SMALL_FAST_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0"

# --- 4. Claude Code 설치 확인 ---
echo ""
if command -v claude > /dev/null 2>&1; then
    echo "✅ Claude Code가 설치되어 있습니다."
    echo ""
    echo "========================================="
    echo "  준비 완료! 아래 명령으로 실행하세요:"
    echo "  $ claude"
    echo "========================================="
else
    echo "❌ Claude Code가 설치되어 있지 않습니다."
    echo "   설치: npm install -g @anthropic-ai/claude-code"
fi
