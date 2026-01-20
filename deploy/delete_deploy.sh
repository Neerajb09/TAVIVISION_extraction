#!/bin/bash
set -e

# =========================
# CONFIG
# =========================
AWS_REGION="ap-south-1"

ENDPOINT_NAME="tavivision-endpoint-v2-1"
ENDPOINT_CONFIG_NAME="tavivision-endpoint-v2-1-config-night"
# MODEL_NAME="tavivision-model-v2-1"
ECR_REPO_NAME="tavi-extraction"

# =========================
# FUNCTIONS
# =========================

delete_endpoint() {
  echo "Deleting endpoint: $ENDPOINT_NAME"

  if aws sagemaker describe-endpoint --endpoint-name "$ENDPOINT_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws sagemaker delete-endpoint --endpoint-name "$ENDPOINT_NAME" --region "$AWS_REGION"
    echo "Waiting for endpoint deletion..."
    aws sagemaker wait endpoint-deleted --endpoint-name "$ENDPOINT_NAME" --region "$AWS_REGION"
    echo "Endpoint deleted ✅"
  else
    echo "Endpoint not found, skipping ⚠️"
  fi
}

delete_endpoint_config() {
  echo "Deleting endpoint config: $ENDPOINT_CONFIG_NAME"

  if aws sagemaker describe-endpoint-config --endpoint-config-name "$ENDPOINT_CONFIG_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws sagemaker delete-endpoint-config --endpoint-config-name "$ENDPOINT_CONFIG_NAME" --region "$AWS_REGION"
    echo "Endpoint config deleted ✅"
  else
    echo "Endpoint config not found, skipping ⚠️"
  fi
}

delete_model() {
  echo "Deleting model: $MODEL_NAME"

  if aws sagemaker describe-model --model-name "$MODEL_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws sagemaker delete-model --model-name "$MODEL_NAME" --region "$AWS_REGION"
    echo "Model deleted ✅"
  else
    echo "Model not found, skipping ⚠️"
  fi
}

delete_ecr_repo() {
  echo "Deleting ECR repository: $ECR_REPO_NAME"

  if aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws ecr delete-repository \
      --repository-name "$ECR_REPO_NAME" \
      --region "$AWS_REGION" \
      --force
    echo "ECR repository deleted ✅"
  else
    echo "ECR repo not found, skipping ⚠️"
  fi
}

# =========================
# EXECUTION ORDER (IMPORTANT)
# =========================

# delete_endpoint
delete_endpoint_config
# delete_model
delete_ecr_repo

echo "========================================"
echo " SageMaker cleanup completed successfully 🎉"
echo "========================================"
