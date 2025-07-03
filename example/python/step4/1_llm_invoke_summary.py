import json
import boto3
from example.python.common.opensearch import client

# --- 1. 설정 ---
# 검색할 벡터 인덱스 이름
index_name = 'bedrock-test'
# 사용할 Amazon Bedrock Embedding 모델 ID
embedding_model_id = 'amazon.titan-embed-text-v2:0'
# 요약에 사용할 Amazon Bedrock LLM 모델 ID
# LLM_MODEL_ID = ""
# llm_model_id = 'us.anthropic.claude-opus-4-20250514-v1:0'
# llm_model_id = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
llm_model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
# Bedrock 클라이언트를 생성할 AWS 리전
aws_region = 'us-east-1'
# 사용자 검색어
user_query = "s3와 cloudfront"

# --- 2. Bedrock 클라이언트 생성 ---
# 이 과정은 AWS 자격 증명이 설정되어 있어야 합니다.
try:
    # 사용할 AWS 프로필을 지정하여 세션을 먼저 생성합니다.
    print("Creating a boto3 session with profile 'skku-opensearch-session'...")
    session = boto3.Session(profile_name='skku-opensearch-session')

    # 생성된 세션에서 Bedrock 클라이언트를 가져옵니다.
    print(f"Creating a Bedrock client in region: {aws_region}")
    bedrock_client = session.client(
        service_name='bedrock-runtime',
        region_name=aws_region,
    )
    print("Bedrock client created successfully.")
except Exception as e:
    print(f"Error creating Bedrock client: {e}")
    exit()

# --- 3. Bedrock에서 텍스트 임베딩을 가져오는 함수 ---
def get_embedding_from_bedrock(text, model_id):
    """
    Bedrock API를 호출하여 주어진 텍스트의 벡터 임베딩을 반환합니다.
    """
    body = json.dumps({"inputText": text})
    response = bedrock_client.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
    )
    response_body = json.loads(response.get("body").read())
    return response_body.get("embedding")

# --- 4. OpenSearch에서 k-NN 검색 수행 ---
print(f"\n1. Generating embedding for the user query: '{user_query}'")
try:
    # 사용자 쿼리를 벡터로 변환
    query_vector = get_embedding_from_bedrock(user_query, embedding_model_id)
    print("   - Embedding generated successfully.")
except Exception as e:
    print(f"Error generating embedding: {e}")
    exit()

print("\n2. Performing k-NN search on OpenSearch...")
# k-NN 검색 쿼리 정의
knn_query = {
    "size": 5,  # 5개의 결과만 가져옴
    "query": {
        "knn": {
            "content_vector": {
                "vector": query_vector,
                "k": 5
            }
        }
    },
    # 필요한 필드만 가져오도록 설정
    "_source": ["title", "content", "author", "post_id"]
}

try:
    # OpenSearch 클라이언트로 검색 실행
    response = client.search(
        index=index_name,
        body=knn_query
    )
    print("   - Search completed successfully.")
except Exception as e:
    print(f"Error during k-NN search: {e}")
    exit()

# 검색 결과에서 문서 내용 추출
hits = response["hits"]["hits"]
if not hits:
    print("No matching documents found.")
    exit()

print(f"\n3. Found {len(hits)} relevant documents:")
# 검색된 문서들의 제목 출력
for i, hit in enumerate(hits):
    print(f"   - Doc {i+1}: {hit['_source']['title']} (Score: {hit['_score']})")

# --- 5. 검색 결과를 LLM으로 요약 ---
# 요약할 내용을 하나의 문자열로 합치기
context_for_llm = ""
for hit in hits:
    context_for_llm += f"문서 제목: {hit['_source']['title']}\n"
    context_for_llm += f"문서 내용: {hit['_source']['content']}\n\n"

# LLM에 전달할 프롬프트 생성
prompt = f"""
Human: 다음은 OpenSearch 검색 결과입니다. 이 내용을 바탕으로 사용자의 질문에 대해 한국어로 친절하게 요약해 주세요. 대신 질문과 관련 없는 결과는 제외하고 요약해주세요. 그리고 제외된 결과는 마지막에 글 제목 리스트를 알려주세요.

[검색 결과]
{context_for_llm}

[질문]
{user_query}

Assistant:
"""

print("\n4. Summarizing the search results using Bedrock LLM...")

# Bedrock LLM(Claude 3) 호출을 위한 Body 구성
body = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 2048,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]
})

try:
    # Bedrock LLM 호출
    response = bedrock_client.invoke_model(
        body=body,
        modelId=llm_model_id,
        accept="application/json",
        contentType="application/json"
    )
    response_body = json.loads(response.get('body').read())
    summary = response_body['content'][0]['text']
    print("   - Summarization completed successfully.")

    # --- 6. 최종 결과 출력 ---
    print("\n" + "="*50)
    print(" [최종 요약 결과] ")
    print("="*50)
    print(summary)
    print("="*50)

except Exception as e:
    print(f"Error during summarization with Bedrock: {e}")
    exit()