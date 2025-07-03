# 검색할 텍스트
from sentence_transformers import SentenceTransformer

from example.python.common.opensearch import client

# --- 1. 설정 ---
# 검색에 필요한 설정들을 상단에 모아두면 관리가 편합니다.
INDEX_NAME = 'vector-test'
QUERY_TEXT = "s3랑 cloudfront를 활용해서 정적 웹사이트를 배포하는 방법 알려줘"
EMBEDDING_MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

# --- 2. 임베딩 모델 로드 및 벡터 변환 ---
# 모델 로드는 비용이 큰 작업이므로, 스크립트 실행 시 한 번만 수행하는 것이 좋습니다.
print(f"Loading embedding model: '{EMBEDDING_MODEL_NAME}'...")
model = SentenceTransformer(EMBEDDING_MODEL_NAME)

print(f"Creating a vector for the query: '{QUERY_TEXT}'...")
query_vector = model.encode(QUERY_TEXT).tolist()

# --- 3. k-NN 검색 쿼리 실행 ---
# k는 필수 파라미터이므로 주석을 해제해야 합니다.
# 일반적으로 k와 size를 동일한 값으로 설정합니다.
K_NEIGHBORS = 5
RESULT_SIZE = 5

search_query = {
    "size": RESULT_SIZE,
    "query": {
        "knn": {
            "content_vector": {
                "vector": query_vector,
                "k": K_NEIGHBORS  # k는 필수입니다. 주석을 해제합니다.
            }
        }
    }
}

print(f"Searching for top {RESULT_SIZE} similar documents...")
# 검색 실행
response = client.search(
    index=INDEX_NAME,
    body=search_query
)

# --- 4. 결과 출력 ---
hits = response['hits']['hits']
print(f"\n--- '{QUERY_TEXT}'와(과) 유사한 문서 검색 결과({len(hits)}) ---")

if not hits:
    print("검색된 문서가 없습니다.")
else:
    for i, hit in enumerate(hits):
        score = hit['_score']
        title = hit['_source'].get('title', 'N/A')
        content = hit['_source'].get('content', 'N/A')
        print(f"\n[{i+1}] 유사도: {score:.4f}")
        print(f"    제목: {title}")
        print(f"    내용: {content[:100]}...") # 내용이 길 경우 100자만 미리보기
