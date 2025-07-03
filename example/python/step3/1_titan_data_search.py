import json
import boto3
from opensearchpy.exceptions import RequestError

from example.python.common import config
from example.python.common.opensearch import client

# --- 1. 설정 ---
# 검색에 필요한 설정들을 상단에 모아두면 관리가 편합니다.
INDEX_NAME = 'bedrock-test'
QUERY_TEXT = "s3랑 cloudfront를 활용해서 정적 웹사이트를 배포하는 방법 알려줘"

# 데이터 업로드 시 사용했던 것과 "반드시 동일한" 모델과 설정을 사용해야 합니다.
EMBEDDING_MODEL_ID = 'amazon.titan-embed-text-v2:0'

# --- 2. Bedrock 클라이언트 생성 ---
try:
    print(f"Creating a boto3 session with profile '{config.PROFILE}'...")
    session = boto3.Session(profile_name=config.PROFILE)

    print(f"Creating a Bedrock client in region: {config.BEDROCK_REGION}")
    bedrock_client = session.client(
        service_name='bedrock-runtime',
        region_name=config.BEDROCK_REGION,
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

# --- 4. 검색어 벡터 변환 ---
try:
    print(f"Creating a vector for the query: '{QUERY_TEXT}'...")
    query_vector = get_embedding_from_bedrock(QUERY_TEXT, EMBEDDING_MODEL_ID)
    if not query_vector:
        print("Failed to create a vector for the query.")
        exit()
except Exception as e:
    print(f"An error occurred during vector creation: {e}")
    exit()

# --- 5. k-NN 검색 쿼리 실행 ---
K_NEIGHBORS = 5
RESULT_SIZE = 5

search_query = {
    "size": RESULT_SIZE,
    "query": {
        "knn": {
            "content_vector": {
                "vector": query_vector,
                "k": K_NEIGHBORS
            }
        }
    }
}

print(f"Searching for top {RESULT_SIZE} similar documents in index '{INDEX_NAME}'...")

try:
    # 검색 실행
    response = client.search(
        index=INDEX_NAME,
        body=search_query
    )

    # --- 6. 결과 출력 (가독성 개선) ---
    hits = response['hits']['hits']
    print(f"\n--- '{QUERY_TEXT}'와(과) 유사한 문서 검색 결과({len(hits)}) ---")

    if not hits:
        print("검색된 문서가 없습니다.")
        print("팁: INDEX_NAME이 정확한지, 데이터가 정상적으로 업로드되었는지 확인해보세요.")
    else:
        for i, hit in enumerate(hits):
            score = hit['_score']
            title = hit['_source'].get('title', 'N/A')
            content = hit['_source'].get('content', 'N/A')

            # 각 결과를 여러 줄로 나누어 명확하게 출력
            print(f"\n[{i + 1}] 유사도: {score:.4f}")
            print(f"    제목: {title}")
            print(f"    내용: {content[:150]}...")

except RequestError as e:
    print("\n[!!!] 검색 중 에러가 발생했습니다.")
    print(f"상태 코드: {e.status_code}")
    print(f"에러 정보: {e.error}")
    print(f"에러 원인: {e.info.get('error', {}).get('root_cause', [{}])[0].get('reason', '알 수 없음')}")
except Exception as e:
    print(f"\n[!!!] 예상치 못한 에러가 발생했습니다: {e}")