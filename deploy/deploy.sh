#!/bin/bash
set -e

# =========================
# CONFIG
# =========================
AWS_REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="tavi-extraction"
IMAGE_TAG="latest"

ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG"

echo "Using ECR URI: $ECR_URI"

# =========================
# CREATE ECR REPO (if not exists)
# =========================
echo "Creating ECR repository (if not exists)..."

aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION >/dev/null 2>&1 || \
aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION

# =========================
# LOGIN TO ECR
# =========================
echo "Logging in to ECR..."

aws ecr get-login-password --region $AWS_REGION | \
docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# =========================
# BUILD IMAGE
# =========================
echo "Building Docker image..."

docker build -t $REPO_NAME -f ../Dockerfile ..

# =========================
# TAG IMAGE
# =========================
echo "Tagging image..."

docker tag $REPO_NAME:latest $ECR_URI

# =========================
# PUSH IMAGE
# =========================
echo "Pushing image to ECR..."

docker push $ECR_URI

# =========================
# DONE
# =========================
echo "======================================="
echo "Docker image successfully pushed!"
echo "ECR Image URI:"
echo $ECR_URI
echo "======================================="
