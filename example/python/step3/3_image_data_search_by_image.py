import json
import boto3
import base64
import os
from opensearchpy.exceptions import RequestError

from example.python.common import config
from example.python.common.opensearch import client

# --- 1. 설정 ---
# 이미지 검색에 필요한 설정으로 변경합니다.
INDEX_NAME = 'bedrock-image-test'
# 검색의 기준이 될 이미지 파일 경로
QUERY_IMAGE_PATH = 'example/sample_data/image/bee_1.png'

# 데이터 업로드 시 사용했던 것과 "반드시 동일한" 모델을 사용해야 합니다.
EMBEDDING_MODEL_ID = 'amazon.titan-embed-image-v1'

# --- 2. Bedrock 클라이언트 생성 ---
# 이 부분은 수정할 필요가 없습니다.
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

# --- 3. 이미지 처리를 위한 함수 추가 및 수정 ---
def image_to_base64(image_path):
    """
    이미지 파일 경로를 받아 Base64로 인코딩된 문자열을 반환합니다.
    """
    if not os.path.exists(image_path):
        print(f"Error: Query image file not found at {image_path}")
        return None
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def get_image_embedding_from_bedrock(base64_image_data, model_id):
    """
    Bedrock API를 호출하여 Base64 이미지 데이터의 벡터 임베딩을 반환합니다.
    """
    # API 요청 본문 형식을 'inputImage'로 변경합니다.
    body = json.dumps({"inputImage": base64_image_data})
    response = bedrock_client.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
    )
    response_body = json.loads(response.get("body").read())
    return response_body.get("embedding")

# --- 4. 검색 이미지 벡터 변환 ---
try:
    print(f"Creating a vector for the query image: '{QUERY_IMAGE_PATH}'...")
    # 이미지를 Base64로 인코딩
    base64_data = image_to_base64(QUERY_IMAGE_PATH)
    if not base64_data:
        exit()

    # Base64 데이터를 사용하여 벡터 생성
    query_vector = get_image_embedding_from_bedrock(base64_data, EMBEDDING_MODEL_ID)
    if not query_vector:
        print("Failed to create a vector for the query image.")
        exit()
except Exception as e:
    print(f"An error occurred during vector creation: {e}")
    exit()

# --- 5. k-NN 검색 쿼리 실행 ---
# 이 부분은 수정할 필요가 없습니다.
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

print(f"Searching for top {RESULT_SIZE} similar images in index '{INDEX_NAME}'...")

try:
    # 검색 실행
    response = client.search(
        index=INDEX_NAME,
        body=search_query
    )

    # --- 6. 결과 출력 (이미지 검색에 맞게 수정) ---
    hits = response['hits']['hits']
    print(f"\n--- '{QUERY_IMAGE_PATH}'와(과) 유사한 이미지 검색 결과({len(hits)}) ---")

    if not hits:
        print("검색된 이미지가 없습니다.")
        print("팁: INDEX_NAME이 정확한지, 이미지가 정상적으로 업로드되었는지 확인해보세요.")
    else:
        for i, hit in enumerate(hits):
            score = hit['_score']
            # 결과에서 'image_path' 필드를 가져옵니다.
            image_path = hit['_source'].get('image_path', 'N/A')

            # 이미지 검색 결과에 맞게 출력 형식을 변경합니다.
            print(f"\n[{i + 1}] 유사도: {score:.4f}")
            print(f"    이미지 경로: {image_path}")

except RequestError as e:
    print("\n[!!!] 검색 중 에러가 발생했습니다.")
    print(f"상태 코드: {e.status_code}")
    print(f"에러 정보: {e.error}")
    print(f"에러 원인: {e.info.get('error', {}).get('root_cause', [{}])[0].get('reason', '알 수 없음')}")
except Exception as e:
    print(f"\n[!!!] 예상치 못한 에러가 발생했습니다: {e}")
