terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0" # 유연한 버전 관리를 위해 ~> 6.0 사용을 권장합니다.
    }
  }
}

# 기본 프로바이더 및 리전 설정
provider "aws" {
  region = "ap-northeast-2"

  # ~/.aws/credentials 파일에 설정된 프로필 이름을 지정합니다.
  profile = "skku-opensearch"

  default_tags {
    tags = {
      "terraform" = "true"
      "project"   = "skku-kdt-opensearch" # 프로젝트명
    }
  }
}

# ----------------------------------------------------
# 데이터 소스 (현재 AWS 계정 정보 가져오기)
# ----------------------------------------------------
data "aws_caller_identity" "current" {}

# ----------------------------------------------------
# OpenSearch Serverless 보안 정책
# ----------------------------------------------------

# 1. 암호화 정책: 데이터가 저장될 때 어떻게 암호화할지 정의합니다.
#    (AWS 소유 키를 사용한 기본 암호화 설정)
resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name   = "${var.student_id}-policy"
  type   = "encryption"
  policy = jsonencode({
    "Rules" : [
      {
        "ResourceType" : "collection",
        "Resource" : [
          "collection/${var.student_id}"
        ]
      }
    ],
    "AWSOwnedKey" : true
  })
}

# 2. 네트워크 정책: 누가, 어떻게 이 컬렉션에 접근할 수 있는지 네트워크 레벨에서 정의합니다.
#    (주의: 교육 목적으로 대시보드에 'Public' 접근을 허용합니다.)
resource "aws_opensearchserverless_security_policy" "network_policy" {
  name   = "${var.student_id}-policy"
  type   = "network"
  policy = jsonencode([
    {
      "Description" : "Allow public access to the OpenSearch Dashboards",
      "Rules" : [
        {
          "ResourceType" : "dashboard",
          "Resource" : [
            "collection/${var.student_id}"
          ]
        },
        {
          "ResourceType" : "collection",
          "Resource" : [
            "collection/${var.student_id}"
          ]
        }
      ],
      "AllowFromPublic" : true
    }
  ])
}

# ----------------------------------------------------
# OpenSearch Serverless 데이터 접근 정책
# ----------------------------------------------------

# 3. 데이터 접근 정책: 어떤 IAM 사용자/역할이 데이터를 읽고 쓸 수 있는지 권한을 정의합니다.
resource "aws_opensearchserverless_access_policy" "data_access_policy" {
  name   = "${var.student_id}-policy"
  type   = "data"
  policy = jsonencode([
    {
      "Description" : "Allow the current user to manage the collection data",
      "Rules" : [
        {
          "ResourceType" : "index",
          "Resource" : [
            "index/*/*" # 컬렉션 내 모든 인덱스에 대한 권한
          ],
          "Permission" : [
            "aoss:*" # 모든 데이터 관련 작업 허용
          ]
        }
      ],
      # Terraform을 실행하는 현재 IAM 사용자/역할에 권한 부여
      "Principal" : [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      ]
    }
  ])
}

# ----------------------------------------------------
# OpenSearch Serverless 컬렉션 (핵심 리소스)
# ----------------------------------------------------
resource "aws_opensearchserverless_collection" "main" {
  # 컬렉션 이름은 계정 및 리전 내에서 고유해야 합니다.
  name = "${var.student_id}"
  # type = "SEARCH" # 일반 검색 용도
  type = "VECTORSEARCH" # 벡터 검색과 일반 검색 모두 지원


  # 정책들이 먼저 생성되도록 의존성 명시
  depends_on = [
    aws_opensearchserverless_security_policy.encryption_policy,
    aws_opensearchserverless_security_policy.network_policy,
  ]
}

# ----------------------------------------------------
# 출력 (Output)
# ----------------------------------------------------

# 생성된 OpenSearch Serverless 컬렉션의 데이터 엔드포인트
output "collection_endpoint" {
  description = "The data endpoint for the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.main.collection_endpoint
}

# OpenSearch Dashboards URL
output "dashboard_endpoint" {
  description = "The endpoint for the OpenSearch Dashboards"
  value       = aws_opensearchserverless_collection.main.dashboard_endpoint
}
