import json
import boto3
from opensearchpy import helpers
from example.python.common.opensearch import client

# --- 1. 설정 ---
# 새로 생성할 벡터 인덱스 이름
index_name = 'bedrock-test'
# 사용할 JSON 파일 경로
json_file_path = 'example/sample_data/json_data.json'
# 사용할 Amazon Bedrock Embedding 모델 ID
embedding_model_id = 'amazon.titan-embed-text-v2:0'
# 위 모델의 벡터 차원 수. Titan V2는 1024 차원입니다.
vector_dimension = 1024
# Bedrock 클라이언트를 생성할 AWS 리전
aws_region = 'us-east-1'

# --- 2. Bedrock 클라이언트 생성 ---
# 이 과정은 AWS 자격 증명이 설정되어 있어야 합니다.
try:
    # 1. 사용할 AWS 프로필을 지정하여 세션을 먼저 생성합니다.
    print("Creating a boto3 session with profile 'skku-opensearch-session'...")
    session = boto3.Session(profile_name='skku-opensearch-session')

    # 2. 생성된 세션에서 Bedrock 클라이언트를 가져옵니다.
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

# --- 4. 벡터 인덱스 매핑 정의 ---
# k-NN 벡터 검색을 위한 인덱스 설정 및 매핑
index_body = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,
            "analysis": {
                "analyzer": {
                    "korean_nori_analyzer": {
                        "type": "custom",
                        "tokenizer": "nori_tokenizer",
                        "filter": [
                            "nori_part_of_speech",
                            "nori_readingform",
                            "lowercase"
                        ]
                    }
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "content_vector": {
                "type": "knn_vector",
                "dimension": vector_dimension, # Titan V2 모델의 차원 수로 변경
                "method": {
                    "name": "hnsw",
                    # cosinesimil 대신 innerproduct 사용
                    "space_type": "innerproduct",
                    # OpenSearch Serverless에 더 최적화된 faiss 엔진 사용
                    "engine": "faiss"
                }
            },
            "post_id": {"type": "integer"},
            "title": {"type": "text", "analyzer": "korean_nori_analyzer"},
            "content": {"type": "text", "analyzer": "korean_nori_analyzer"},
            "author": {"type": "keyword"},
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "created_at": {"type": "date"}
        }
    }
}

# --- 5. 인덱스 생성 ---
# 인덱스가 이미 존재하면 삭제하고 새로 생성 (실습의 편의를 위해)
try:
    if client.indices.exists(index=index_name):
        print(f"Deleting existing index '{index_name}'...")
        client.indices.delete(index=index_name)
    print(f"Creating new index '{index_name}'...")
    client.indices.create(index=index_name, body=index_body)
    print(f"Index '{index_name}' created successfully.")
except Exception as e:
    print(f"An error occurred during index creation: {e}")
    exit()

# --- 6. JSON 데이터 로드 ---
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    print(f"Successfully loaded {len(documents)} documents from '{json_file_path}'.")
except Exception as e:
    print(f"Error loading JSON file: {e}")
    exit()

# --- 7. 데이터 임베딩 및 Bulk API를 사용하여 대량 업로드 ---
def generate_bulk_actions(docs, idx_name):
    """
    문서들을 순회하며 Bedrock으로 벡터 임베딩을 생성하고,
    Bulk API 형식에 맞는 JSON 객체를 생성(yield)하는 함수
    """
    for index, doc in enumerate(docs):
        text_to_embed = f"{doc.get('title', '')}\n{doc.get('content', '')}"

        # Bedrock API를 호출하여 텍스트를 벡터로 변환
        vector = get_embedding_from_bedrock(text_to_embed, embedding_model_id)

        if not vector:
            print(f"Warning: Could not generate embedding for doc_id {doc.get('post_id')}. Skipping.")
            continue
        else:
            print(f"[{index+1}/{len(docs)}] embedding | vector = {vector}")

        source_data = {
            "content_vector": vector,
            "post_id": doc.get("post_id"),
            "title": doc.get("title"),
            "content": doc.get("content"),
            "author": doc.get("author"),
            "category": doc.get("category"),
            "tags": doc.get("tags"),
            "created_at": doc.get("created_at")
        }

        yield {
            "_index": idx_name,
            "_source": source_data
        }

try:
    print("Starting data embedding and uploading via Bedrock...")
    success, failed = helpers.bulk(client, generate_bulk_actions(documents, index_name))

    print(f"Successfully indexed {success} documents.")
    if failed:
        print(f"Failed to index {len(failed)} documents.")
        for i, item in enumerate(failed[:5]):
            print(f"Failed item {i+1}: {item}")

except Exception as e:
    print(f"An error occurred during bulk indexing: {e}")