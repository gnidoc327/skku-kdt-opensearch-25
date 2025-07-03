import json
from time import sleep

from opensearchpy import helpers
from sentence_transformers import SentenceTransformer, util

from example.python.common.opensearch import client

# --- 1. 설정 ---
# 새로 생성할 벡터 인덱스 이름
index_name = 'vector-test'
# 사용할 JSON 파일 경로
json_file_path = 'example/sample_data/json_data.json'
# 사용할 Sentence Transformer 모델. 한국어 포함 다국어에 성능이 좋은 모델입니다.
embedding_model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
# 위 모델의 벡터 차원 수. 모델마다 다르므로 확인이 필요합니다. (이 모델은 384)
vector_dimension = 384

# --- 2. 임베딩 모델 로드 ---
# 이 과정은 모델을 다운로드해야 하므로 처음 실행 시 시간이 걸릴 수 있습니다.
try:
    print(f"Loading embedding model '{embedding_model_name}'...")
    model = SentenceTransformer(embedding_model_name)
    # ~/.cache/huggingface/hub/ 경로에 다운로드됩니다.
    print("Embedding model loaded successfully.")
except Exception as e:
    print(f"Error loading embedding model: {e}")
    exit()

# --- 3. 벡터 인덱스 매핑 정의 ---
# k-NN 벡터 검색을 위한 인덱스 설정 및 매핑
index_body = {
    "settings": {
        "index": {
            "knn": True,  # k-NN 검색을 활성화합니다.
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
            # 텍스트를 벡터로 변환하여 저장할 필드
            "content_vector": {
                "type": "knn_vector",
                "dimension": vector_dimension,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib"
                }
            },
            # 원본 데이터를 함께 저장할 필드들
            "post_id": {"type": "integer"},
            "title": {"type": "text", "analyzer": "korean_nori_analyzer"},
            "content": {"type": "text", "analyzer": "korean_nori_analyzer"},
            "author": {"type": "keyword"},
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"}, # 배열 형태의 태그는 keyword 타입으로 지정
            "created_at": {"type": "date"}
        }
    }
}

if not client.indices.exists(index=index_name):
    try:
        print(f"Creating new index '{index_name}' with nori analyzer...")
        response = client.indices.create(index=index_name, body=index_body)
        print(f"Index '{index_name}' created successfully.")
        sleep(5)
    except Exception as e:
        print(f"Error creating index '{index_name}': {e}")
        exit()

# --- 4. JSON 데이터 로드 ---
try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    print(f"Successfully loaded {len(documents)} documents from '{json_file_path}'.")
except FileNotFoundError:
    print(f"Error: The file '{json_file_path}' was not found.")
    exit()
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from the file '{json_file_path}'.")
    exit()


# --- 5. 데이터 임베딩 및 Bulk API를 사용하여 대량 업로드 ---
def generate_bulk_actions(docs, idx_name):
    """
    문서들을 순회하며 벡터 임베딩을 생성하고,
    Bulk API 형식에 맞는 JSON 객체를 생성(yield)하는 함수
    """
    for doc in docs:
        # 벡터로 변환할 텍스트. 여기서는 제목과 내용을 합쳐서 사용합니다.
        text_to_embed = f"{doc.get('title', '')}\n{doc.get('content', '')}"

        # 텍스트를 벡터로 변환
        vector = model.encode(text_to_embed).tolist()

        # OpenSearch에 저장할 문서(_source)를 구성합니다.
        # 원본 필드와 벡터 필드를 모두 포함합니다.
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

        # _id 필드를 제거합니다. OpenSearch Serverless가 ID를 자동 생성합니다.
        yield {
            "_index": idx_name,
            "_source": source_data
        }


try:
    print("Starting data embedding and uploading...")
    # helpers.bulk를 사용하여 대량의 문서를 효율적으로 색인
    success, failed = helpers.bulk(client, generate_bulk_actions(documents, index_name))

    print(f"Successfully indexed {success} documents.")
    if failed:
        print(f"Failed to index {len(failed)} documents.")
        for i, item in enumerate(failed[:5]): # 실패 항목은 최대 5개까지만 출력
            print(f"Failed item {i+1}: {item}")

except Exception as e:
    print(f"An error occurred during bulk indexing: {e}")
