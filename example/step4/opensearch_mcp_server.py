"""
OpenSearch MCP Server
=====================
ReAct Agent가 사용할 OpenSearch 검색 도구를 MCP 프로토콜로 제공합니다.

제공 도구:
  - search_documents: 텍스트 문서 벡터 검색 (bedrock-test 인덱스)
  - search_images: 이미지 벡터 검색 (nova-image-test 인덱스)

실행 방법:
  이 파일은 직접 실행하지 않습니다.
  노트북에서 MCP 클라이언트가 subprocess로 자동 실행합니다.
"""

import os
import json
import math

import boto3
from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection
from mcp.server.fastmcp import FastMCP

# --- 설정 (환경변수에서 읽기) ---
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
    """Titan 텍스트 임베딩 (영어 최적화)"""
    body = json.dumps({"inputText": text})
    resp = bedrock_client.invoke_model(
        body=body,
        modelId="amazon.titan-embed-text-v2:0",
        accept="application/json",
        contentType="application/json",
    )
    return json.loads(resp["body"].read()).get("embedding")


def _nova_text_embedding(text):
    """Nova 멀티모달 텍스트 임베딩 (한국어 포함 다국어)"""
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


# --- MCP 서버 정의 ---
mcp = FastMCP("opensearch-search")


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
            image_path = hit["_source"].get("image_path", "N/A")
            results.append(
                f"[{i+1}] (유사도: {hit['_score']:.3f}) 이미지 경로: {image_path}"
            )
        return "\n\n".join(results)
    except Exception as e:
        return f"검색 중 오류 발생: {e}"


if __name__ == "__main__":
    mcp.run()
