# Step 6. Claude Code + Amazon Bedrock

Amazon Bedrock의 Claude 모델을 사용하여 **Claude Code**(AI 코딩 에이전트)를 실행하는 방법을 알아봅니다.

Claude Code는 터미널에서 동작하는 AI 코딩 도우미로, 코드 작성/수정/디버깅/리팩토링 등을 자연어로 요청할 수 있습니다.

---

## 1. Claude Code 설치

### 1-1. Node.js 설치

Claude Code는 Node.js 18 이상이 필요합니다.

```bash
# Homebrew로 Node.js 설치
brew install node

# 설치 확인
node --version   # v18 이상
npm --version
```

> Homebrew가 없다면 먼저 설치하세요:
> ```bash
> /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
> ```

### 1-2. Claude Code 설치

```bash
# npm으로 전역 설치
npm install -g @anthropic-ai/claude-code

# 설치 확인
claude --version
```

---

## 2. 환경 변수 설정

### 방법 A: 수동 설정 (터미널에서 직접)

```bash
# 1. AWS 세션 토큰 갱신 (이미 했다면 생략)
./get-session-token.sh

# 2. Bedrock 사용 활성화
export CLAUDE_CODE_USE_BEDROCK=1

# 3. AWS 리전 설정 (필수 - Claude Code는 .aws/config를 읽지 않음)
export AWS_REGION=us-east-1

# 4. AWS 프로파일 설정
export AWS_PROFILE=skku-opensearch-session

# 5. 모델 설정 (us. 접두사 사용)
export ANTHROPIC_MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0
export ANTHROPIC_SMALL_FAST_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0

# 6. Claude Code 실행!
claude
```

### 방법 B: 설정 스크립트 사용

```bash
# 스크립트 실행
source example/step6/setup-claude-code.sh

# Claude Code 실행
claude
```

### 방법 C: 프로젝트 설정 파일 사용 (권장)

프로젝트 루트에 `.claude/settings.json` 파일을 생성하면 매번 환경변수를 설정할 필요가 없습니다:

```json
{
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-east-1",
    "AWS_PROFILE": "skku-opensearch-session",
    "ANTHROPIC_MODEL": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "ANTHROPIC_SMALL_FAST_MODEL": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  }
}
```

---

## 3. 모델 설정 (선택사항)

Bedrock에서 사용 가능한 Claude 모델:

| 모델 | 모델 ID | 특징 |
|------|---------|------|
| **Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | 최고 성능, 복잡한 작업에 적합 |
| **Sonnet 4.5** | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | 성능과 속도의 균형 |
| **Haiku 4.5** | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 가장 빠름, `/fast` 모드용 |

기본값은 Sonnet 4.5입니다. Opus 4.6을 사용하고 싶다면:

```bash
# Opus 4.6을 메인 모델로 사용
export ANTHROPIC_MODEL='us.anthropic.claude-opus-4-6-v1'
```

> **모델 ID 접두사 차이:**
> - `us.` : 미국 리전 내에서 분산 처리 (Cross-Region Inference)
> - `global.` : 미국 + 유럽 등 전 세계 리전에 분산 처리
>
> 이번 실습에서는 `us.` 접두사를 사용합니다.

---

## 4. Claude Code 사용해보기

### 기본 사용법

```bash
# 프로젝트 루트에서 실행
cd /path/to/project
claude

# 또는 질문을 바로 전달
claude "이 프로젝트의 구조를 설명해줘"
```

### 유용한 명령어

| 명령어 | 설명 |
|--------|------|
| `/help` | 도움말 |
| `/fast` | 빠른 모드 토글 (Haiku 모델 사용) |
| `/clear` | 대화 초기화 |
| `/compact` | 대화 컨텍스트 압축 |
| `Ctrl+C` | 현재 작업 중단 |
| `Escape` (2회) | 대화 종료 |

### 실습 예시

Claude Code를 실행한 후 아래 질문들을 시도해보세요:

```
# 1. 프로젝트 구조 파악
이 프로젝트의 폴더 구조와 각 step이 무슨 역할인지 설명해줘

# 2. 코드 설명
example/step4/opensearch_mcp_server.py 파일을 분석해서 설명해줘

# 3. 코드 수정 요청
search_mcp_server.py에 날씨 검색 도구를 추가해줘

# 4. 버그 찾기
step5/0_chainlit.py에서 개선할 점이 있는지 리뷰해줘

# 5. 테스트 작성
search_mcp_server.py의 _titan_text_embedding 함수에 대한 단위 테스트를 작성해줘
```

---

## 5. 세션 토큰 자동 갱신 설정

AWS STS 세션 토큰이 만료되면 Claude Code가 동작하지 않습니다.
자동 갱신을 설정하려면 `.claude/settings.json`에 추가합니다:

```json
{
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "us-east-1",
    "AWS_PROFILE": "skku-opensearch-session"
  },
  "awsAuthRefresh": "./get-session-token.sh"
}
```

이렇게 설정하면 토큰 만료 시 Claude Code가 자동으로 `get-session-token.sh`를 실행합니다.

---

## 6. 실습 과제: MCP 서버 만들어보기

Claude Code에게 MCP 서버를 만들어달라고 요청해보세요. 아래 3가지 중 하나를 골라서 시도해봅니다.

### 과제 A: 메모장 MCP

로컬 파일에 메모를 저장하고 조회하는 MCP 서버입니다.

```
메모장 MCP 서버를 만들어줘.
FastMCP를 사용하고 아래 도구를 구현해줘:
- add_memo: 제목과 내용으로 메모 추가 (JSON 파일에 저장)
- list_memos: 저장된 메모 목록 조회
- search_memos: 키워드로 메모 검색
- delete_memo: 메모 삭제
```

> 외부 라이브러리 없이 `json` 모듈만으로 구현 가능합니다.

### 과제 B: 계산기 MCP

다양한 계산을 수행하는 MCP 서버입니다.

```
계산기 MCP 서버를 만들어줘.
FastMCP를 사용하고 아래 도구를 구현해줘:
- calculate: 수학 표현식 계산 (예: "3 * 4 + 2")
- unit_convert: 단위 변환 (예: km→mile, kg→lb, 섭씨→화씨)
- percentage: 퍼센트 계산 (예: 1500의 30%)
```

> `math` 모듈만으로 구현 가능합니다. 보안을 위해 `eval()` 대신 안전한 파싱을 사용하도록 요청해보세요.

### 과제 C: 위키피디아 MCP

위키피디아에서 정보를 검색하는 MCP 서버입니다.

```
위키피디아 MCP 서버를 만들어줘.
FastMCP를 사용하고 아래 도구를 구현해줘:
- search_wiki: 키워드로 위키피디아 문서 검색
- get_summary: 특정 문서의 요약 가져오기
- get_sections: 문서의 목차(섹션 목록) 가져오기
wikipedia 패키지를 사용해줘.
```

```bash
# 패키지 설치
pip install wikipedia
```

### 만든 MCP 서버 테스트하기

만든 서버를 Step 5의 Chainlit 챗봇에 연결하거나, 노트북에서 테스트할 수 있습니다:

```python
from mcp.server.fastmcp import FastMCP

# 터미널에서 직접 실행하여 테스트
# python my_mcp_server.py
```

---

## 7. 주의사항

- `AWS_REGION` 환경변수는 **필수**입니다. Claude Code는 `~/.aws/config` 파일의 리전 설정을 읽지 않습니다.
- Bedrock 모드에서는 `/login`, `/logout` 명령이 비활성화됩니다 (AWS 인증 사용).
- 프롬프트 캐싱이 지원되지 않는 리전에서는 `export DISABLE_PROMPT_CACHING=1`을 설정하세요.
- 비용은 Bedrock 사용량 기준으로 AWS 계정에 청구됩니다.

---

## 8. 참고 링크

- [Claude Code 공식 문서](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Claude Code + Bedrock 설정 가이드](https://docs.anthropic.com/en/docs/claude-code/bedrock) — 버전 업그레이드 시 이 문서를 참고하세요
- [Bedrock 지원 모델 및 추론 프로파일 목록](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html) — 새 모델 ID 확인용
- [Amazon Bedrock 콘솔](https://console.aws.amazon.com/bedrock/)
