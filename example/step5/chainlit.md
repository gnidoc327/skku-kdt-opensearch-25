# Step 5. AI Agent 챗봇 (Chainlit + MCP)

OpenSearch 벡터 검색, 웹 검색, Amazon Bedrock Claude를 활용한 AI Agent 챗봇입니다.
에이전트가 질문에 따라 적절한 도구를 자동 선택하여 답변합니다.

## 사전 조건

- **Step 0** 완료 → `config.json` 생성 (OpenSearch/Bedrock 접속 정보)
- **Step 3-0** 완료 → `bedrock-test` 인덱스에 텍스트 문서가 업로드된 상태
- **Step 3-2** 완료 → `nova-image-test` 인덱스에 이미지 데이터가 업로드된 상태 (이미지 검색용)
- **AWS 세션 토큰**이 유효한 상태 (`get-session-token.sh` 실행)

## 패키지 설치

```bash
pip install boto3==1.38.46 opensearch-py==2.8.0 chainlit==2.9.6 \
            langchain-mcp-adapters==0.2.1 langchain-aws==1.2.3 langgraph==1.0.8 \
            ddgs==9.10.0
```

## 실행 방법

```bash
cd example/step5
chainlit run 0_chainlit.py -w
```

브라우저에서 `http://localhost:8000` 이 자동으로 열립니다.
`-w` 옵션은 코드 수정 시 자동 리로드합니다.

## 사용 방법

1. 아래 입력창에 질문을 입력하세요
2. AI 에이전트가 질문을 분석하여 적절한 도구를 선택합니다
3. 도구 실행 과정이 **Step UI**로 실시간 표시됩니다
4. 검색 결과를 바탕으로 Claude가 **스트리밍**으로 답변을 생성합니다
5. 답변 아래에 참고 자료가 표시됩니다

## 사용 가능한 도구

| 도구 | 설명 | 예시 질문 |
|------|------|-----------|
| 📄 문서 검색 | OpenSearch 텍스트 벡터 검색 | "s3랑 관련있는 글 찾아서 요약해줘" |
| 🖼️ 이미지 검색 | OpenSearch 이미지 벡터 검색 | "강아지 이미지 찾아줘" |
| 🌐 웹 검색 | DuckDuckGo 웹 검색 | "2026년 최신 AI 트렌드 알려줘" |

## 실습 과제

1. 다양한 질문으로 에이전트가 어떤 도구를 선택하는지 관찰해보세요
2. `search_mcp_server.py`에 새로운 도구를 추가해보세요
