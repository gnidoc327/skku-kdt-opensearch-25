import json
import boto3
import base64
import os

from opensearchpy.exceptions import RequestError

from example.python.common import config
from example.python.common.opensearch import client

# --- 1. 설정 ---
# 텍스트-이미지 검색을 위한 멀티모달 설정
MULTIMODAL_INDEX_NAME = 'bedrock-image-test'
MULTIMODAL_EMBEDDING_MODEL_ID = 'amazon.titan-embed-image-v1'

# 이미지 분석 및 설명을 위한 LLM 설정(inference profile ID)
# LLM_MODEL_ID = "us.anthropic.claude-opus-4-20250514-v1:0"
# LLM_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

# --- 2. Bedrock 클라이언트 생성 ---
try:
    print(f"Creating a boto3 session with profile '{config.PROFILE}'...")
    session = boto3.Session(profile_name=config.PROFILE)
    print(f"Creating a Bedrock client in region: {config.BEDROCK_REGION}")
    bedrock_client = session.client(
        "bedrock-runtime",
        region_name=config.BEDROCK_REGION,
    )
    print("Bedrock client created successfully.")
except Exception as e:
    print(f"Error creating Bedrock client: {e}")
    exit()

# --- 3. 필요한 함수 정의 ---

def get_text_embedding(text, model_id):
    """멀티모달 모델을 사용하여 텍스트를 벡터로 변환합니다."""
    body = json.dumps({"inputText": text})
    response = bedrock_client.invoke_model(
        body=body, modelId=model_id, accept="application/json", contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    return response_body.get("embedding")

def search_similar_image(index_name, query_vector):
    """OpenSearch에서 벡터 검색을 수행하여 가장 유사한 이미지 경로를 반환합니다."""
    search_query = {
        "size": 1,  # 가장 유사한 이미지 1개만 필요
        "query": {"knn": {"content_vector": {"vector": query_vector, "k": 1}}}
    }
    try:
        response = client.search(index=index_name, body=search_query)
        hits = response['hits']['hits']
        if not hits:
            return None
        return hits[0]['_source'].get('image_path')
    except RequestError as e:
        print(f"Error during OpenSearch search: {e.info}")
        return None

def image_to_base64(image_path):
    """이미지 파일을 Base64로 인코딩합니다."""
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return None
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def get_image_description_from_llm(base64_image, user_question):
    """Claude Sonnet 모델에게 이미지를 보여주고 설명을 요청합니다."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "temperature": 0.7,
        "top_p": 0.9,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image},
                    },
                    {
                        "type": "text",
                        "text": f"이 이미지는 '{user_question}'이라는 질문으로 검색된 결과입니다. 이미지에 대해 친절하고 상세하게 설명해주세요."
                    }
                ],
            }
        ]
    })

    response = bedrock_client.invoke_model(
        body=body, modelId=LLM_MODEL_ID, accept="application/json", contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    return response_body['content'][0]['text']

# --- 4. 메인 실행 로직 ---
if __name__ == "__main__":
    # 1. 사용자 질문 입력
    # user_query = input("어떤 이미지를 찾아드릴까요? (예: 풀밭에서 쉬고 있는 강아지) > ")
    user_query = "꽃 위에 벌"
    if not user_query:
        print("검색어를 입력해주세요.")
        exit()

    try:
        # 2. 텍스트-이미지 검색
        print(f"\n1. '{user_query}'와(과) 유사한 이미지를 검색합니다...")
        query_vector = get_text_embedding(user_query, MULTIMODAL_EMBEDDING_MODEL_ID)
        if not query_vector:
            raise ValueError("쿼리 벡터를 생성하지 못했습니다.")

        found_image_path = search_similar_image(MULTIMODAL_INDEX_NAME, query_vector)
        if not found_image_path:
            print("관련 이미지를 찾지 못했습니다. 다른 검색어를 시도해보세요.")
            exit()

        print(f"   - 이미지 찾음: {found_image_path}")

        # 3. 이미지 분석 및 설명 생성
        print("\n2. 찾은 이미지를 분석하여 설명을 생성합니다...")
        base64_image_data = image_to_base64(found_image_path)
        if not base64_image_data:
            raise ValueError("이미지를 Base64로 변환하지 못했습니다.")

        description = get_image_description_from_llm(base64_image_data, user_query)

        # 4. 최종 결과 출력
        print("\n--- 최종 결과 ---")
        print(f"✅ 검색된 이미지: {found_image_path}")
        print("\n✅ 이미지 설명:")
        print(description)

    except Exception as e:
        print(f"\n[!!!] 처리 중 오류가 발생했습니다: {e}")
