import json
import boto3
from opensearchpy.exceptions import RequestError

from example.python.common import config
from example.python.common.opensearch import client

# --- 1. 설정 ---
# 멀티모달 검색을 위한 설정
# 멀티모달 모델로 임베딩된 데이터가 있는 인덱스를 사용해야 합니다.
INDEX_NAME = 'bedrock-image-test'

# 텍스트 키워드로 검색합니다.
QUERY_TEXT = "말벌"

# 멀티모달 임베딩 모델 ID
EMBEDDING_MODEL_ID = 'amazon.titan-embed-image-v1'

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

# --- 3. Bedrock에서 텍스트 임베딩을 가져오는 함수 (멀티모달용) ---
def get_text_embedding_from_multimodal_model(text, model_id):
    """
    멀티모달 모델을 호출하여 텍스트의 벡터 임베딩을 반환합니다.
    """
    # 멀티모달 모델은 텍스트 입력을 위해 'inputText' 파라미터를 사용합니다.
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
    print(f"Creating a vector for the query text: '{QUERY_TEXT}'...")
    query_vector = get_text_embedding_from_multimodal_model(QUERY_TEXT, EMBEDDING_MODEL_ID)
    if not query_vector:
        print("Failed to create a vector for the query text.")
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

print(f"Searching for top {RESULT_SIZE} similar images for '{QUERY_TEXT}'...")

# --- 6. 검색 실행 및 결과 출력 ---
try:
    response = client.search(index=INDEX_NAME, body=search_query)
    hits = response['hits']['hits']
    print(f"\n--- '{QUERY_TEXT}'와(과) 유사한 이미지 검색 결과({len(hits)}) ---")

    if not hits:
        print("검색된 이미지가 없습니다.")
        print("팁: 멀티모달 모델로 데이터가 업로드된 인덱스가 맞는지 확인해보세요.")
    else:
        for i, hit in enumerate(hits):
            score = hit['_score']
            image_path = hit['_source'].get('image_path', 'N/A')
            print(f"\n[{i + 1}] 유사도: {score:.4f}")
            print(f"    이미지 경로: {image_path}")

except RequestError as e:
    print(f"\n[!!!] 검색 중 에러가 발생했습니다: {e.info}")
except Exception as e:
    print(f"\n[!!!] 예상치 못한 에러가 발생했습니다: {e}")
