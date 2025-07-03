import json
import boto3
import os
import base64
from opensearchpy import helpers

from example.python.common import config
from example.python.common.opensearch import client

# --- 1. 설정 ---
# 새로 생성할 이미지 벡터 인덱스 이름
INDEX_NAME = 'bedrock-image-test'
# 이미지가 저장된 디렉토리 경로
IMAGE_DIRECTORY_PATH = 'example/sample_data/image'
# 사용할 Amazon Bedrock Embedding 모델 ID
EMBEDDING_MODEL_ID = 'amazon.titan-embed-image-v1'
# 위 모델의 벡터 차원 수. Titan Image V1은 1024 차원입니다.
VECTOR_DIMENSION = 1024
# Bedrock 클라이언트를 생성할 AWS 리전

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

# --- 3. 이미지 파일을 Base64로 인코딩하는 함수 ---
def image_to_base64(image_path):
    """
    이미지 파일 경로를 받아 Base64로 인코딩된 문자열을 반환합니다.
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return None
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

# --- 4. Bedrock에서 이미지 임베딩을 가져오는 함수 ---
def get_image_embedding_from_bedrock(base64_image_data, model_id):
    """
    Bedrock API를 호출하여 Base64 이미지 데이터의 벡터 임베딩을 반환합니다.
    """
    # API 요청 본문 형식이 텍스트 임베딩과 다릅니다. (inputText -> inputImage)
    body = json.dumps({"inputImage": base64_image_data})
    response = bedrock_client.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
    )
    response_body = json.loads(response.get("body").read())
    return response_body.get("embedding")

# --- 5. 벡터 인덱스 매핑 정의 ---
# 이미지 검색에 필요한 최소한의 필드로 구성합니다.
index_body = {
    "settings": {
        "index": {
            "knn": True,
        }
    },
    "mappings": {
        "properties": {
            "content_vector": {
                "type": "knn_vector",
                "dimension": VECTOR_DIMENSION,
                "method": {
                    "name": "hnsw",
                    "space_type": "innerproduct",
                    "engine": "faiss"
                }
            },
            # 이미지 파일 경로를 저장할 필드
            "image_path": {"type": "keyword"},
        }
    }
}

# --- 6. 인덱스 생성 ---
try:
    if client.indices.exists(index=INDEX_NAME):
        print(f"Deleting existing index '{INDEX_NAME}'...")
        client.indices.delete(index=INDEX_NAME)

    print(f"Creating new index '{INDEX_NAME}'...")
    client.indices.create(index=INDEX_NAME, body=index_body)
    print(f"Index '{INDEX_NAME}' created successfully.")
except Exception as e:
    print(f"An error occurred during index creation: {e}")
    exit()

# --- 7. 이미지 파일 목록 로드 ---
try:
    print(f"Loading image files from '{IMAGE_DIRECTORY_PATH}'...")
    # 디렉토리에서 .png, .jpg, .jpeg 확장자를 가진 파일만 필터링합니다.
    image_files = [f for f in os.listdir(IMAGE_DIRECTORY_PATH) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print(f"No image files found in '{IMAGE_DIRECTORY_PATH}'. Please check the directory.")
        exit()
    print(f"Found {len(image_files)} image files.")
except Exception as e:
    print(f"Error accessing image directory: {e}")
    exit()

# --- 8. 데이터 임베딩 및 Bulk API를 사용하여 대량 업로드 ---
def generate_bulk_actions(img_files, img_dir):
    """
    이미지 파일들을 순회하며 Bedrock으로 벡터 임베딩을 생성하고,
    Bulk API 형식에 맞는 JSON 객체를 생성(yield)하는 함수
    """
    for i, file_name in enumerate(img_files):
        print(f"  - Processing image {i+1}/{len(img_files)}: {file_name}")
        full_path = os.path.join(img_dir, file_name)

        # 이미지를 Base64로 인코딩
        base64_data = image_to_base64(full_path)
        if not base64_data:
            continue

        # Bedrock API를 호출하여 벡터 생성
        vector = get_image_embedding_from_bedrock(base64_data, EMBEDDING_MODEL_ID)
        if not vector:
            print(f"Warning: Could not generate embedding for {file_name}. Skipping.")
            continue

        source_data = {
            "content_vector": vector,
            "image_path": full_path,
        }

        yield {
            "_index": INDEX_NAME,
            "_source": source_data
        }

try:
    print("\nStarting image embedding and uploading via Bedrock...")
    success, failed = helpers.bulk(client, generate_bulk_actions(image_files, IMAGE_DIRECTORY_PATH))

    print(f"\nSuccessfully indexed {success} images.")
    if failed:
        print(f"Failed to index {len(failed)} images.")
        for i, item in enumerate(failed[:5]):
            print(f"Failed item {i+1}: {item}")

except Exception as e:
    print(f"An error occurred during bulk indexing: {e}")