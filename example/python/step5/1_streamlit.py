"""
- Okt가 자바가 필수라서 설치가 필요합니다.
- PC마다 상태가 다를 수 있으니 꼭 아래와 똑같이 진행하실 필요는 없고 터미널에서 확인해가면서 복붙하시면 됩니다.

brew install openjdk@17
sudo ln -sfn $(brew --prefix)/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk
echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 17)' >> ~/.zshrc
source ~/.zshrc
echo $JAVA_HOME
streamlit run example/python/step5/1_streamlit.py
"""
import os
import streamlit as st
import json
import boto3
import sys
from collections import Counter

# --- WordCloud 관련 라이브러리 ---
from wordcloud import WordCloud
from konlpy.tag import Okt # 한글 형태소 분석기

# --- 프로젝트 루트 경로를 sys.path에 추가 ---
# 이 코드는 스크립트가 어디서 실행되든, 프로젝트의 최상위 디렉토리를
# 파이썬 모듈 검색 경로에 포함시켜 'from common import ...' 구문을 가능하게 합니다.
try:
    current_file_path = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from example.python.common.opensearch import client
    from example.python.common import config
except (IndexError, ModuleNotFoundError):
    st.error("프로젝트 경로 설정에 실패했습니다. 'common' 모듈을 찾을 수 없습니다. 스크립트 위치를 확인해주세요.")
    st.stop()
# ---------------------------------------------


# --- 1. 환경 설정 및 클라이언트 초기화 ---
try:
    session = boto3.Session(profile_name=config.PROFILE)
    bedrock = session.client(
        service_name='bedrock-runtime',
        region_name=config.BEDROCK_REGION,
    )

    # 상수 정의
    BEDROCK_EMBED_MODEL_ID = 'amazon.titan-embed-text-v2:0'
    OPENSEARCH_INDEX_NAME = 'bedrock-test'

except Exception as e:
    st.error(f"클라이언트 초기화 중 오류가 발생했습니다: {e}")
    st.info("OpenSearch 및 AWS 자격증명 관련 환경 변수가 올바르게 설정되었는지 확인해주세요.")
    st.stop()


# --- 2. 핵심 기능 함수 정의 ---

@st.cache_data
def get_embedding_from_titan(text: str):
    """Bedrock Titan 임베딩 모델을 호출하여 텍스트의 벡터를 생성합니다."""
    body = json.dumps({"inputText": text})
    response = bedrock.invoke_model(
        body=body,
        modelId=BEDROCK_EMBED_MODEL_ID,
        accept='application/json',
        contentType='application/json'
    )
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

def search_opensearch_vector(query: str, top_k: int = 5):
    """사용자 질문을 벡터로 변환하고 OpenSearch에서 k-NN 벡터 검색을 수행합니다."""
    print(f"벡터 검색 시작: '{query}' (상위 {top_k}개)")

    query_vector = get_embedding_from_titan(query)

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
        "_source": ["title", "content"] # 워드클라우드에 필요한 필드만 요청
    }

    response = client.search(
        index=OPENSEARCH_INDEX_NAME,
        body=search_query
    )
    return [hit['_source'] for hit in response['hits']['hits']]

@st.cache_data
def create_word_cloud_from_docs(documents: list):
    """검색된 문서들의 'content'를 기반으로 워드클라우드 이미지를 생성합니다."""
    # 폰트 경로 설정 (프로젝트 루트의 fonts 폴더)
    font_path = os.path.join(project_root, 'example/sample_data/fonts', 'NanumGothic-Regular.ttf')
    if not os.path.exists(font_path):
        st.warning("폰트 파일('example/sample_data/fonts/NanumGothic-Regular.ttf')을 찾을 수 없습니다. 워드클라우드가 정상적으로 보이지 않을 수 있습니다.")
        return None

    # 모든 문서의 'content'를 하나의 문자열로 합치기
    text = " ".join([doc.get('content', '') for doc in documents])
    if not text.strip():
        st.info("워드클라우드를 생성할 텍스트가 없습니다.")
        return None

    # Okt 형태소 분석기로 명사만 추출
    okt = Okt()
    nouns = okt.nouns(text)
    words = [n for n in nouns if len(n) > 1] # 두 글자 이상인 명사만 필터링

    if not words:
        st.info("워드클라우드를 생성할 키워드(명사)가 충분하지 않습니다.")
        return None

    counter = Counter(words)
    wc = WordCloud(
        font_path=font_path,
        width=800,
        height=400,
        background_color='white'
    ).generate_from_frequencies(counter)

    return wc.to_image()


# --- 3. Streamlit UI 구성 ---

st.set_page_config(page_title="키워드 워드클라우드 생성기", page_icon="☁️")
st.title("📝 OpenSearch 검색 결과로 워드클라우드 만들기")
st.write("질문을 입력하면 OpenSearch에서 관련 문서 5개를 찾아 핵심 키워드를 워드클라우드로 보여줍니다.")

# 사용자 질문 입력
user_question = st.text_input("궁금한 주제를 입력하세요:", placeholder="예: 모니터 충전 기능")

if user_question:
    with st.spinner("OpenSearch에서 관련 문서를 찾고 워드클라우드를 생성하는 중입니다..."):
        # 1. OpenSearch에서 관련 문서 5개 검색
        retrieved_docs = search_opensearch_vector(user_question, top_k=5)

        if not retrieved_docs:
            st.warning("관련 문서를 찾지 못했습니다. 다른 키워드로 검색해보세요.")
        else:
            # 2. 검색된 문서 목록 표시 (옵션)
            st.subheader(f"🔍 검색된 문서 (상위 {len(retrieved_docs)}개)")
            for doc in retrieved_docs:
                st.write(f"- {doc.get('title', '제목 없음')}")

            # 3. 워드클라우드 생성 및 표시
            st.subheader("✨ 핵심 키워드 (Word Cloud)")
            wordcloud_image = create_word_cloud_from_docs(retrieved_docs)

            if wordcloud_image:
                st.image(wordcloud_image)
            else:
                st.error("워드클라우드 이미지 생성에 실패했습니다.")