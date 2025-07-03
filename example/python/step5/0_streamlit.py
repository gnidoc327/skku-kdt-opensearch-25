# streamlit run example/python/step5/0_streamlit.py
# s3랑 관련있는 글 찾아서 요약해줘
import os
import streamlit as st
import json
import boto3
import sys

# --- 프로젝트 루트 경로를 sys.path에 추가 ---
# 이 코드는 스크립트가 어디서 실행되든, 프로젝트의 최상위 디렉토리를
# 파이썬 모듈 검색 경로에 포함시켜 'from common import ...' 구문을 가능하게 합니다.
# 현재 파일의 절대 경로
current_file_path = os.path.abspath(__file__)
# 프로젝트 루트 디렉토리 (현재 파일 위치에서 세 단계 위)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
# sys.path에 프로젝트 루트 추가
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ---------------------------------------------
from example.python.common.opensearch import client
from example.python.common import config


# --- 1. 환경 설정 및 클라이언트 초기화 ---
session = boto3.Session(profile_name=config.PROFILE)
bedrock = session.client(
    service_name='bedrock-runtime',
    region_name=config.BEDROCK_REGION,
)

# 클라이언트 가져오기
try:
    # 상수 정의
    BEDROCK_EMBED_MODEL_ID = 'amazon.titan-embed-text-v2:0'
    BEDROCK_LLM_MODEL_ID = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
    OPENSEARCH_INDEX_NAME = 'bedrock-test' # OpenSearch 인덱스 이름

except Exception as e:
    st.error(f"클라이언트 초기화 중 오류가 발생했습니다: {e}")
    st.info("OpenSearch 및 AWS 자격증명 관련 환경 변수가 올바르게 설정되었는지 확인해주세요.")
    st.stop()


# --- 2. 실제 연동 함수 정의 ---

def get_embedding_from_titan(text: str):
    """
    Bedrock Titan 임베딩 모델을 호출하여 텍스트의 벡터를 생성합니다.
    """
    body = json.dumps({"inputText": text})
    response = bedrock.invoke_model(
        body=body,
        modelId=BEDROCK_EMBED_MODEL_ID,
        accept='application/json',
        contentType='application/json'
    )
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

def search_opensearch_vector(query: str, top_k: int = 3):
    """
    사용자 질문을 벡터로 변환하고 OpenSearch에서 k-NN 벡터 검색을 수행합니다.
    """
    print(f"실제 벡터 검색 시작: '{query}'")

    # 1. 사용자 질문을 벡터로 변환
    query_vector = get_embedding_from_titan(query)

    # 2. OpenSearch k-NN 쿼리 구성
    search_query = {
        "size": top_k,
        "query": {
            "knn": {
                "content_vector": {
                    "vector": query_vector,
                    "k": top_k
                }
            }
        },
        "_source": ["title", "content", "author", "post_id"]
    }

    # 3. OpenSearch에 검색 요청
    response = client.search(
        index=OPENSEARCH_INDEX_NAME,
        body=search_query
    )

    # 4. 결과에서 문서(_source)만 추출하여 반환
    retrieved_docs = [hit['_source'] for hit in response['hits']['hits']]
    print(f"검색된 문서: {[doc.get('title', '제목 없음') for doc in retrieved_docs]}")
    return retrieved_docs

def generate_answer_with_bedrock(context_docs: list, question: str):
    """
    Bedrock Claude 3 Sonnet 모델을 호출하여 컨텍스트 기반의 답변을 생성합니다.
    """
    print("실제 Bedrock LLM 답변 생성 시작...")

    if not context_docs:
        return "죄송합니다. 관련 정보를 찾을 수 없어 답변을 드릴 수 없습니다. 다른 질문을 시도해 주세요."

    # 프롬프트 엔지니어링: 컨텍스트와 질문을 조합
    context_str = "\n\n".join([
        f"문서 제목: {doc.get('title', 'N/A')}\n내용: {doc.get('content', 'N/A')}" for doc in context_docs
    ])

    prompt = f"""당신은 주어진 정보를 바탕으로 사용자의 질문에 친절하게 답변하는 AI 어시스턴트입니다.
아래의 '정보'를 참고하여 '질문'에 대해 답변해주세요. 정보에 없는 내용은 답변하지 마세요.

[정보]
{context_str}

[질문]
{question}
"""

    # Bedrock Claude 3 Sonnet 호출 형식
    conversation = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ]

    response = bedrock.invoke_model(
        modelId=BEDROCK_LLM_MODEL_ID,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": conversation,
            }
        ),
    )

    response_body = json.loads(response["body"].read())
    answer = response_body["content"][0]["text"]

    return answer


# --- 3. Streamlit UI 구성 (기존과 거의 동일) ---

st.set_page_config(page_title="RAG 챗봇 데모", page_icon="🤖")

st.title("📦 JSON 데이터 기반 Q&A 챗봇 (RAG 데모)")
st.write("OpenSearch와 Bedrock에 직접 연동하여 답변을 생성합니다.")

# 세션 상태를 사용하여 대화 기록 저장
if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 기록 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "context" in message and message["context"]:
            with st.expander("🔍 참고한 정보 보기"):
                st.json(message["context"])

# 사용자 질문 입력
if user_question := st.chat_input("궁금한 점을 물어보세요! (예: 모니터 충전 기능 알려줘)"):
    # 사용자 질문을 대화 기록에 추가하고 화면에 표시
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # AI 답변 생성
    with st.chat_message("assistant"):
        with st.spinner("정보를 찾고 답변을 생성하는 중..."):
            # 1. [Retrieval] 유사 문서 검색 (실제 OpenSearch 호출)
            retrieved_docs = search_opensearch_vector(user_question)

            # 2. [Generation] LLM으로 답변 생성 (실제 Bedrock 호출)
            answer = generate_answer_with_bedrock(retrieved_docs, user_question)

            # 3. 결과 출력
            st.markdown(answer)

    # AI 답변과 컨텍스트를 대화 기록에 추가
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "context": retrieved_docs # 답변의 근거가 된 문서를 함께 저장
    })