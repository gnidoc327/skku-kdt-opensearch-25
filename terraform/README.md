# Terraform을 이용한 AWS OpenSearch Serverless 구축 가이드
## 1. 개요
- 이 문서는 AWS OpenSearch Serverless를 Terraform을 이용하여 구축하는 과정을 상세하게 안내합니다. 
- Terraform은 HashiCorp에서 개발한 IaC(Infrastructure as Code) 도구입니다.
- 코드를 통해 클라우드 및 온프레미스 리소스를 효율적으로 프로비저닝하고 관리할 수 있게 해줍니다. 
- 이 가이드를 통해 Terraform의 기본적인 사용법을 익히고, AWS OpenSearch Serverless 인프라를 자동으로 생성 및 관리하는 방법을 배울 수 있습니다.

## 2. Terraform 설치
- 링크: https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli
```shell
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```
- zsh 사용자라면 플러그인을 추가하시면 더 편합니다.
- 플러그인 사용시 얻을 수 있는 장점
  - 자동 완성 기능 (Tab Completion): `terraform` 명령어를 입력하고 Tab 키를 누르면 사용 가능한 하위 명령어가 자동으로 표시됩니다.
  - 별칭 (Aliases): `tf`와 같은 짧은 별칭으로 `terraform` 명령어를 실행할 수 있습니다.
```shell
# .zshrc 파일에 다음 라인 추가
plugins=(git terraform)
```

## 3. Terraform 실행
### 초기화(Init)
- Terraform 프로젝트를 시작하기 위해 필요한 AWS 프로바이더 플러그인을 다운로드합니다.
```shell
# cd terraform
terraform init
# tfi
```

### 계획 (Plan)
- Terraform이 AWS에 어떤 변경 사항을 적용할지 미리 확인합니다.
- 이 단계에서는 실제 리소스가 생성되거나 변경되지 않습니다.
- `terraform plan` 명령을 실행하기 전에 AWS 자격 증명이 올바르게 설정되어 있는지 확인해야 합니다.
```shell
# cd terraform
terraform plan
# tfp
```

### 적용 (Apply)
- `terraform apply` 명령을 사용하여 `terraform plan`에서 계획된 변경 사항을 AWS에 적용합니다.
- 이 명령은 실제 AWS 리소스를 생성, 수정 또는 삭제합니다.
- 실행 시, Terraform은 적용될 변경 사항을 다시 한번 요약하여 보여주고, 사용자에게 `yes`를 입력하여 승인할 것을 요청합니다.
- 신중하게 검토한 후 `yes`를 입력하여 진행합니다.
  - 최초 생성시 약 5분정도 소요됩니다.
```shell
# cd terraform
terraform apply
# tfa
```

### 삭제 (Destroy)
- `terraform destroy` 명령을 사용하여 Terraform이 관리하는 모든 AWS 리소스를 삭제합니다.
- 이 명령은 모든 인프라를 해체하므로, 프로덕션 환경에서는 매우 신중하게 사용해야 합니다.
- 실행 시, Terraform은 삭제될 리소스 목록을 보여주고, 사용자에게 `yes`를 입력하여 승인할 것을 요청합니다.
- 신중하게 검토한 후 `yes`를 입력하여 진행합니다.
```shell
# cd terraform
terraform destroy
# tfd
```
