import json
from time import sleep

from opensearchpy import helpers

from example.python.common.opensearch import client

# --- 1. 설정: index_name과 json 파일 경로를 수정합니다. ---
index_name = 'json-test'  # 새로 생성하고 데이터를 업로드할 인덱스 이름
json_file_path = 'example/sample_data/json_data.json' # 업로드할 JSON 파일 경로

# --- 2. 인덱스 삭제 및 재생성 ---
# nori 분석기를 적용한 인덱스 매핑 및 설정 정의
index_body = {
    "settings": {
        "index": {
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
            },
            "number_of_shards": 1,
            "number_of_replicas": 1
        }
    },
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "analyzer": "korean_nori_analyzer"
            },
            "content": {
                "type": "text",
                "analyzer": "korean_nori_analyzer"
            },
            "author": {"type": "keyword"},
            "timestamp": {"type": "date"}
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


# --- 3. Bulk API를 사용하여 데이터 대량 업로드 ---
def generate_bulk_actions(docs, idx_name):
    """Bulk API에 맞는 형식으로 데이터를 가공하는 함수"""
    for doc in docs:
        yield {
            "_index": idx_name,
            "_source": doc
        }

try:
    print("Starting data upload...")
    # helpers.bulk를 사용하여 대량의 문서를 효율적으로 색인
    success, failed = helpers.bulk(client, generate_bulk_actions(documents, index_name))

    print(f"Successfully indexed {success} documents.")
    if failed:
        print(f"Failed to index {len(failed)} documents.")
        # 실패한 경우, 처음 5개의 실패 항목을 출력하여 디버깅에 도움을 줍니다.
        for i, item in enumerate(failed):
            if i >= 5: break
            print(f"Failed item {i+1}: {item}")

except Exception as e:
    print(f"An error occurred during bulk indexing: {e}")
