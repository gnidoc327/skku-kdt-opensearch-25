# =============================================================================
# Step 5-0. AI Agent 챗봇 (Chainlit + MCP)
# 패키지 설치: pip install boto3==1.38.46 opensearch-py==2.8.0 chainlit==2.9.6 \
#              langchain-mcp-adapters==0.2.1 langchain-aws==1.2.3 langgraph==1.0.8 \
#              ddgs==9.10.0
# 실행: cd example/step5 && chainlit run 0_chainlit.py -w
#
# [실습 과제]
# 1. 다양한 질문으로 에이전트가 어떤 도구를 선택하는지 관찰해보세요
#    - "Docker와 Kubernetes 차이점 알려줘" → search_documents
#    - "강아지 이미지 찾아줘" → search_images
#    - "오늘 날씨 알려줘" → web_search
# 2. search_mcp_server.py에 새로운 도구를 추가해보세요
# =============================================================================
import os
import sys
import json
import warnings

import chainlit as cl
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_aws import ChatBedrockConverse

warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- 1. 환경 설정 ---
_config_dir = os.path.dirname(os.path.abspath(__file__))
_config_path = os.path.join(_config_dir, "..", "config.json")
with open(_config_path) as _f:
    _config = json.load(_f)

OPENSEARCH_HOST = _config["OPENSEARCH_HOST"]
DEFAULT_REGION = _config.get("DEFAULT_REGION", "ap-northeast-2")
BEDROCK_REGION = _config.get("BEDROCK_REGION", "us-east-1")
AWS_PROFILE = _config.get("PROFILE", "skku-opensearch-session")
LLM_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

TOOL_LABELS = {
    "search_documents": "📄 문서 검색",
    "search_images": "🖼️ 이미지 검색",
    "web_search": "🌐 웹 검색",
}

# --- 2. LLM + MCP 클라이언트 ---
model = ChatBedrockConverse(
    model_id=LLM_MODEL_ID,
    region_name=BEDROCK_REGION,
    credentials_profile_name=AWS_PROFILE,
)

server_env = os.environ.copy()
server_env.update({
    "OPENSEARCH_HOST": OPENSEARCH_HOST,
    "DEFAULT_REGION": DEFAULT_REGION,
    "BEDROCK_REGION": BEDROCK_REGION,
    "AWS_PROFILE": AWS_PROFILE,
})

mcp_client = MultiServerMCPClient({
    "search": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(_config_dir, "search_mcp_server.py")],
        "env": server_env,
    }
})

_agent = None


async def get_agent():
    global _agent
    if _agent is None:
        tools = await mcp_client.get_tools()
        _agent = create_react_agent(model, tools)
    return _agent


# --- 3. 도구 결과 → 참고자료 포맷팅 ---

def _extract_tool_output(event_data):
    """on_tool_end 이벤트에서 텍스트를 추출합니다."""
    output = event_data.get("output", "")
    if hasattr(output, "content"):
        content = output.content
        if isinstance(content, list):
            return "\n".join(
                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        if isinstance(content, str):
            return content
    return str(output)


def _format_web_search_refs(output):
    """웹 검색 결과를 마크다운 링크로 포맷팅합니다."""
    refs = ""
    for group in output.split("\n\n"):
        lines = group.strip().split("\n")
        if len(lines) < 2:
            continue
        title = lines[0].lstrip("[0123456789] ")
        url = next((l[5:] for l in lines if l.startswith("URL: ")), "")
        refs += f"\n- [{title}]({url})" if url else f"\n- {title}"
    return refs


def _format_document_refs(output):
    """문서 검색 결과를 제목+미리보기로 포맷팅합니다."""
    refs = ""
    for group in output.split("\n\n"):
        lines = group.strip().split("\n")
        if not lines:
            continue
        title_line = lines[0]
        title = title_line.split(") ", 1)[1] if ") " in title_line else title_line
        preview = next((l[4:][:80] + "..." for l in lines if l.startswith("내용: ")), "")
        refs += f"\n- **{title}**"
        if preview:
            refs += f"\n  > {preview}"
    return refs


def _format_image_refs(output):
    """이미지 검색 결과를 인라인 이미지로 포맷팅합니다."""
    refs = ""
    images = []
    idx = 0
    for line in output.split("\n"):
        if "이미지 경로:" not in line:
            continue
        image_path = line.split("이미지 경로: ")[-1].strip()
        abs_path = image_path if os.path.isabs(image_path) else os.path.normpath(os.path.join(_config_dir, image_path))
        if not os.path.isfile(abs_path):
            refs += f"\n- `{rel_path}` (파일 없음)"
            continue
        idx += 1
        images.append(cl.Image(name=f"search_result_{idx}", path=abs_path, display="inline"))
        score = ""
        if "유사도:" in line:
            score = f" (유사도: {line.split('유사도: ')[1].split(')')[0]})"
        refs += f"\n- **이미지 {idx}**{score}\n"
    return refs, images


_REF_FORMATTERS = {
    "web_search": lambda output: (_format_web_search_refs(output), []),
    "search_documents": lambda output: (_format_document_refs(output), []),
    "search_images": _format_image_refs,
}


def build_references(tool_results):
    """도구 결과 목록을 참고자료 마크다운 + 이미지 요소로 변환합니다."""
    if not tool_results:
        return "", []
    refs = "\n\n---\n**📚 참고 자료**\n"
    all_images = []
    for tr in tool_results:
        formatter = _REF_FORMATTERS.get(tr["name"])
        if formatter:
            text, images = formatter(tr["output"])
            refs += text
            all_images.extend(images)
    return refs, all_images


# --- 4. Chainlit 이벤트 핸들러 ---

@cl.on_chat_start
async def start():
    await get_agent()
    await cl.Message(
        content="안녕하세요! OpenSearch와 웹 검색을 활용한 AI 챗봇입니다.\n"
                "궁금한 점을 물어보세요!\n\n"
                "예시:\n"
                "- `s3랑 관련있는 글 찾아서 요약해줘` (문서 검색)\n"
                "- `강아지 이미지 찾아줘` (이미지 검색)\n"
                "- `2026년 최신 AI 트렌드 알려줘` (웹 검색)"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    agent = await get_agent()
    msg = cl.Message(content="")
    tool_results = []
    current_step = None

    async for event in agent.astream_events(
        {"messages": [("user", message.content)]},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_tool_start":
            label = TOOL_LABELS.get(event["name"], f"🔧 {event['name']}")
            current_step = cl.Step(name=label, type="tool")
            current_step.input = event["data"].get("input", {}).get("query", "")
            await current_step.__aenter__()

        elif kind == "on_tool_end":
            output_text = _extract_tool_output(event["data"])
            tool_results.append({"name": event["name"], "output": output_text})
            if current_step:
                current_step.output = output_text[:500] + ("..." if len(output_text) > 500 else "")
                await current_step.__aexit__(None, None, None)
                current_step = None

        elif kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = ""
            if isinstance(chunk.content, str):
                text = chunk.content
            elif isinstance(chunk.content, list):
                text = "".join(
                    b.get("text", "") for b in chunk.content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if text:
                await msg.stream_token(text)

    refs, images = build_references(tool_results)
    if refs:
        msg.content += refs
    if images:
        msg.elements = images
    await msg.send()
