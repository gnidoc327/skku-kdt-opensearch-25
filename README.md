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
> Pycharm(Jetbrains / Intellij + Python Plugin), Visual Studio Code(vscode) 등 취향껏 사용
##### Pycharm: 학생 라이센스로 유료 라이센스를 무료로 사용 가능!
- 다운로드: https://www.jetbrains.com/pycharm/download/
  - 학생 라이센스 발급이 귀찮다면 하단의 community 버전 사용
- 신청 링크: https://www.jetbrains.com/academy/student-pack/ 
- 저희 학교 이메일은 안되네요?
  - [차단된 도메인(이메일주소)의 경우엔 사용 불가능](https://blog.jetbrains.com/ko/blog/2024/04/12/why-cant-i-get-a-student-license/#%ED%95%99%EA%B5%90-%EC%9D%B4%EB%A9%94%EC%9D%BC-%EC%A3%BC%EC%86%8C%EB%A5%BC-%EC%82%AC%EC%9A%A9%ED%95%98%EC%97%AC-jetbrains-%ED%95%99%EC%83%9D-%EB%9D%BC%EC%9D%B4%EC%84%A0%EC%8A%A4%EB%A5%BC-%EB%B0%9B%EC%9D%84-%EC%88%98-%EC%97%86%EB%8A%94-%EC%9D%B4%EC%9C%A0%EB%8A%94-%EB%AC%B4%EC%97%87%EC%9D%B8%EA%B0%80%EC%9A%94)
  - GitHub Student Developer Pack으로 대신 학생 인증 가능
    - [GitHub Student Developer Pack 신청](https://education.github.com/pack) 
    - [GitHub계정으로 인증하는 방법](https://blog.jetbrains.com/ko/blog/2024/04/12/why-cant-i-get-a-student-license/#%ED%95%99%EC%83%9D-%EB%9D%BC%EC%9D%B4%EC%84%A0%EC%8A%A4%EB%A5%BC-%EB%B0%9B%EA%B8%B0-%EC%9C%84%ED%95%B4%EC%84%9C%EB%8A%94-%EC%96%B4%EB%96%BB%EA%B2%8C-%ED%95%B4%EC%95%BC-%ED%95%98%EB%82%98%EC%9A%94)
##### Visual Studio Code
- 다운로드: https://code.visualstudio.com/Download
- 플러그인
  - Python: `ms-python.python`
  - Pylance: `ms-python.vscode-pylance`

## 4. Python
> 버전: 3.12 이상
##### 설치방법(brew)
```shell
brew install python@3.12
```

## 5. Poetry
> 버전: 2.1.3 이상
##### Poetry란?
- Python 의존성 관리 및 패키징 도구입니다.
- 프로젝트의 의존성을 선언하고 관리하며, 패키지를 빌드하고 게시하는 데 사용됩니다.
- 공식문서: https://python-poetry.org/docs/

##### 설치방법
```shell
# poetry 설치
curl -sSL https://install.python-poetry.org | python3 -
# poetry shell(plugin) 설치
poetry self add poetry-plugin-export
# 설정 변경
poetry config virtualenvs.in-project true
```

##### 가상환경 생성
```shell
poetry env use python3.12
poetry shell
poetry install --no-root
```

##### 프로그램 실행
- pycharm 사용시 [ctrl + alt + R]로 실행 가능
```shell
poetry run python example/python/0-test.py
```

## 6. Terraform
> [terraform/README.md](terraform/README.md) 에서 확인