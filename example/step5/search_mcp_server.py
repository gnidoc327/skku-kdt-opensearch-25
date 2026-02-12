"""
Search MCP Server (Step 5)
==========================
Chainlit 챗봇이 사용할 검색 도구를 MCP 프로토콜로 제공합니다.

제공 도구:
  - search_documents: OpenSearch 텍스트 문서 벡터 검색
  - search_images: OpenSearch 이미지 벡터 검색
  - web_search: DuckDuckGo 웹 검색
"""

import os
import json
import math

import boto3
from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection
from mcp.server.fastmcp import FastMCP
from ddgs import DDGS

# --- 설정 ---
_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_IMAGE_DIR = os.path.normpath(os.path.join(_SERVER_DIR, "..", "..", "data", "image"))

HOST = os.environ["OPENSEARCH_HOST"]
DEFAULT_REGION = os.environ.get("DEFAULT_REGION", "ap-northeast-2")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "skku-opensearch-session")

# --- OpenSearch 클라이언트 ---
credentials = boto3.Session(profile_name=PROFILE).get_credentials()
auth = AWSV4SignerAuth(credentials, DEFAULT_REGION, "aoss")
os_client = OpenSearch(
    hosts=[{"host": HOST, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300,
)

# --- Bedrock 클라이언트 ---
session = boto3.Session(profile_name=PROFILE)
bedrock_client = session.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _normalize_vector(vec):
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm > 0 else vec


def _titan_text_embedding(text):
    body = json.dumps({"inputText": text})
    resp = bedrock_client.invoke_model(
        body=body,
        modelId="amazon.titan-embed-text-v2:0",
        accept="application/json",
        contentType="application/json",
    )
    return json.loads(resp["body"].read()).get("embedding")


def _nova_text_embedding(text):
    body = json.dumps({
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingPurpose": "GENERIC_RETRIEVAL",
            "embeddingDimension": 1024,
            "text": {"truncationMode": "END", "value": text},
        },
    })
    resp = bedrock_client.invoke_model(
        body=body,
        modelId="amazon.nova-2-multimodal-embeddings-v1:0",
        accept="application/json",
        contentType="application/json",
    )
    return _normalize_vector(
        json.loads(resp["body"].read())["embeddings"][0]["embedding"]
    )


# --- MCP 서버 ---
mcp = FastMCP("search-server")


@mcp.tool()
def search_documents(query: str) -> str:
    """OpenSearch에서 질문과 관련된 기술 문서를 벡터 검색합니다.
    기술 블로그, 개발 관련 질문에 답변할 때 사용하세요.
    """
    try:
        query_vector = _titan_text_embedding(query)
        response = os_client.search(
            index="bedrock-test",
            body={
                "size": 5,
                "query": {"knn": {"content_vector": {"vector": query_vector, "k": 5}}},
                "_source": ["title", "content", "author"],
            },
        )
        hits = response["hits"]["hits"]
        if not hits:
            return "검색 결과가 없습니다."
        results = []
        for i, hit in enumerate(hits):
            src = hit["_source"]
            results.append(
                f"[{i+1}] (유사도: {hit['_score']:.3f}) {src.get('title', 'N/A')}\n"
                f"작성자: {src.get('author', 'N/A')}\n"
                f"내용: {src.get('content', 'N/A')}"
            )
        return "\n\n".join(results)
    except Exception as e:
        return f"검색 중 오류 발생: {e}"


@mcp.tool()
def search_images(query: str) -> str:
    """OpenSearch에서 질문과 관련된 이미지를 벡터 검색합니다.
    이미지를 찾거나, 동물/사물 등 시각적 콘텐츠를 검색할 때 사용하세요.
    한국어와 영어 모두 지원합니다.
    """
    try:
        query_vector = _nova_text_embedding(query)
        response = os_client.search(
            index="nova-image-test",
            body={
                "size": 3,
                "query": {"knn": {"content_vector": {"vector": query_vector, "k": 3}}},
            },
        )
        hits = response["hits"]["hits"]
        if not hits:
            return "검색 결과가 없습니다."
        results = []
        for i, hit in enumerate(hits):
            raw_path = hit["_source"].get("image_path", "N/A")
            filename = os.path.basename(raw_path)
            image_path = os.path.join(_DATA_IMAGE_DIR, filename)
            results.append(
                f"[{i+1}] (유사도: {hit['_score']:.3f}) 이미지 경로: {image_path}"
            )
        return "\n\n".join(results)
    except Exception as e:
        return f"검색 중 오류 발생: {e}"


@mcp.tool()
def web_search(query: str) -> str:
    """웹에서 최신 정보를 검색합니다.
    OpenSearch에 없는 일반적인 지식이나 최신 뉴스, 트렌드 정보가 필요할 때 사용하세요.
    """
    try:
        results = list(DDGS().text(query, max_results=5))
        if not results:
            return "검색 결과가 없습니다."
        formatted = []
        for i, r in enumerate(results):
            formatted.append(
                f"[{i+1}] {r['title']}\n{r['body']}\nURL: {r['href']}"
            )
        return "\n\n".join(formatted)
    except Exception as e:
        return f"웹 검색 중 오류 발생: {e}"


if __name__ == "__main__":
    mcp.run()
