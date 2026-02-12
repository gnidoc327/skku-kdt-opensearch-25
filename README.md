# AWS Bedrock과 OpenSearch를 활용한 나만의 검색형 AI 만들기
## 1. Homebrew
```shell
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## 2. AWSCLI
##### install
- 설치방법: https://docs.aws.amazon.com/ko_kr/cli/latest/userguide/getting-started-install.html
```shell
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```
##### configure
- 프로파일 설정. 이름을 꼭 `skku-opensearch` 동일하게 설정해주셔야 실습시 혼동이 없습니다.
```shell
aws configure --profile skku-opensearch
#AWS Access Key ID [None]: [엑세스키]
#AWS Secret Access Key [None]: [시크릿키]
#Default region name [None]: ap-northeast-2
#Default output format [None]: json
```
##### sts
- 인증키를 바로 사용할 순 없고 sts 통해서 임시 토큰(1시간 만료)을 생성해서 사용해야 합니다.
- 임시 토큰의 프로파일명: `skku-opensearch-session` 
```shell
./get-session-token.sh
```

## 3. IDE
> 실습은 **Jupyter Notebook(브라우저)** 으로 진행합니다. 별도 IDE 설치 없이 바로 시작할 수 있습니다.
>
> PyCharm이나 VS Code가 이미 있으면 Jupyter 플러그인으로 노트북을 열 수도 있습니다.

<details>
<summary><b>PyCharm (선택)</b> — 학생 라이센스로 유료 버전 무료 사용 가능</summary>

- 다운로드: https://www.jetbrains.com/pycharm/download/
  - 학생 라이센스 발급이 귀찮다면 하단의 community 버전 사용
- 신청 링크: https://www.jetbrains.com/academy/student-pack/
- 저희 학교 이메일은 안되네요?
  - [차단된 도메인(이메일주소)의 경우엔 사용 불가능](https://blog.jetbrains.com/ko/blog/2024/04/12/why-cant-i-get-a-student-license/#%ED%95%99%EA%B5%90-%EC%9D%B4%EB%A9%94%EC%9D%BC-%EC%A3%BC%EC%86%8C%EB%A5%BC-%EC%82%AC%EC%9A%A9%ED%95%98%EC%97%AC-jetbrains-%ED%95%99%EC%83%9D-%EB%9D%BC%EC%9D%B4%EC%84%A0%EC%8A%A4%EB%A5%BC-%EB%B0%9B%EC%9D%84-%EC%88%98-%EC%97%86%EB%8A%94-%EC%9D%B4%EC%9C%A0%EB%8A%94-%EB%AC%B4%EC%97%87%EC%9D%B8%EA%B0%80%EC%9A%94)
  - GitHub Student Developer Pack으로 대신 학생 인증 가능
    - [GitHub Student Developer Pack 신청](https://education.github.com/pack)
    - [GitHub계정으로 인증하는 방법](https://blog.jetbrains.com/ko/blog/2024/04/12/why-cant-i-get-a-student-license/#%ED%95%99%EC%83%9D-%EB%9D%BC%EC%9D%B4%EC%84%A0%EC%8A%A4%EB%A5%BC-%EB%B0%9B%EA%B8%B0-%EC%9C%84%ED%95%B4%EC%84%9C%EB%8A%94-%EC%96%B4%EB%96%BB%EA%B2%8C-%ED%95%B4%EC%95%BC-%ED%95%98%EB%82%98%EC%9A%94)
</details>

<details>
<summary><b>Visual Studio Code (선택)</b></summary>

- 다운로드: https://code.visualstudio.com/Download
- 플러그인
  - Python: `ms-python.python`
  - Pylance: `ms-python.vscode-pylance`
  - Jupyter: `ms-toolsai.jupyter`
</details>

## 4. Python
> 버전: 3.13 이상
##### 설치방법(brew)
```shell
brew install python@3.13
```

## 5. 가상환경 및 Jupyter Notebook 설정

##### 1) 가상환경 생성
```shell
python3.13 -m venv .venv
```

##### 2) 가상환경 활성화
```shell
# macOS/Linux
source .venv/bin/activate
```
> 터미널 프롬프트 앞에 `(.venv)`가 표시되면 활성화된 상태입니다.

##### 3) Jupyter 설치
```shell
pip install jupyter ipykernel
```

##### 4) Jupyter Notebook 실행
```shell
jupyter notebook
```
- 브라우저에서 Jupyter가 열리면 `example/` 폴더로 이동하여 각 step별 `.ipynb` 파일을 실행합니다.
- 각 노트북의 셀을 순서대로 실행하면 됩니다. (Shift + Enter)
- 각 노트북 첫 셀에 `!pip install ...` 명령이 포함되어 있어 실습에 필요한 패키지가 자동으로 설치됩니다.

##### Step5 (Chainlit) 실행
- step5는 Chainlit 앱이므로 터미널에서 직접 실행합니다.
```shell
# 가상환경이 활성화된 상태에서
cd example/step5 && chainlit run 0_chainlit.py -w
```

##### Step6 (Claude Code) 실행
- step6는 Claude Code(AI 코딩 에이전트)를 Bedrock 모델로 사용하는 실습입니다.
```shell
# 환경 설정 스크립트 실행
source example/step6/setup-claude-code.sh

# Claude Code 실행
claude
```

## 실습 커리큘럼
> `example/` 폴더 내 Jupyter Notebook으로 진행

| Step | 주제 | 설명 |
|------|------|------|
| **Step 0** | 환경 설정 | AWS 연결 확인 및 config.json 생성 |
| **Step 1** | 기본 검색 | 인덱스 CRUD, 텍스트 검색, Nori 한국어 분석기, 집계 |
| **Step 2** | 벡터 검색 (로컬) | Sentence Transformers 로컬 모델로 텍스트 벡터 검색 |
| **Step 3** | 벡터 검색 (Bedrock) | Titan/Nova 클라우드 모델로 텍스트·이미지 벡터 검색 |
| **Step 4** | RAG 파이프라인 | 벡터 검색 + Claude LLM으로 답변 생성 및 이미지 분석 |
| **Step 5** | 채팅 앱 | Chainlit + MCP로 AI Agent 챗봇 구현 |
| **Step 6** | Claude Code | Bedrock 모델로 AI 코딩 에이전트 사용 |

#### Step 3 상세
| 노트북 | 설명 |
|--------|------|
| 3-0 | Bedrock Titan 텍스트 임베딩 데이터 업로드 |
| 3-1 | Bedrock Titan 텍스트 벡터 검색 |
| 3-2a | 이미지 임베딩 업로드 — **Titan** (영어 전용) |
| 3-2b | 이미지 임베딩 업로드 — **Nova** (한국어 포함 200개 언어) |
| 3-3 | 이미지로 유사 이미지 검색 (Nova) |
| 3-4 | 텍스트로 이미지 검색 (Nova, 한국어 가능) |

#### Step 4 상세
| 노트북 | 설명 |
|--------|------|
| 4-0 | 이미지 검색 + Claude LLM 이미지 분석 (RAG) |
| 4-1 | 텍스트 검색 + Claude LLM 요약 (RAG) |

## 6. Terraform
> [terraform/README.md](terraform/README.md) 에서 확인