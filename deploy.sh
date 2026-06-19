#!/usr/bin/env bash
# deploy.sh — package and deploy the RAG Lambda + API Gateway
#
# Prerequisites:
#   aws CLI configured (aws configure)
#   python3 + pip
#   The ChromaDB index must already exist at ./Vector_DB\ -\ SEC_Filings/
#
# Usage:
#   export GOOGLE_API_KEY="your-key"
#   export AWS_REGION="us-east-1"          # optional, defaults shown below
#   export S3_BUCKET="your-bucket-name"    # must already exist
#   bash deploy.sh

set -euo pipefail

# ── Config (override via env vars) ─────────────────────────────────────────────
REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${S3_BUCKET:?Set S3_BUCKET to your existing S3 bucket name}"
S3_PREFIX="${S3_PREFIX:-vectordb}"
LAMBDA_FUNCTION="${LAMBDA_FUNCTION:-financial-rag-handler}"
LAMBDA_ROLE_NAME="${LAMBDA_ROLE_NAME:-financial-rag-lambda-role}"
API_NAME="${API_NAME:-financial-rag-api}"
VECTORDB_LOCAL_DIR="${VECTORDB_LOCAL_DIR:-Vector_DB - SEC_Filings}"
GOOGLE_API_KEY="${GOOGLE_API_KEY:?Set GOOGLE_API_KEY}"

# ── Step 1: Upload ChromaDB snapshot to S3 ────────────────────────────────────
echo "==> Packaging ChromaDB index..."
CHROMA_TAR="/tmp/chroma.tar.gz"
tar -czf "$CHROMA_TAR" -C "." "$VECTORDB_LOCAL_DIR"

S3_KEY="${S3_PREFIX}/chroma.tar.gz"
echo "==> Uploading ChromaDB to s3://${S3_BUCKET}/${S3_KEY} ..."
aws s3 cp "$CHROMA_TAR" "s3://${S3_BUCKET}/${S3_KEY}" --region "$REGION"
echo "    Done."

# ── Step 2: Build Lambda deployment package ───────────────────────────────────
echo "==> Installing Lambda dependencies..."
PKG_DIR="$(mktemp -d)/lambda_package"
mkdir -p "$PKG_DIR"
pip install -r lambda/requirements.txt -t "$PKG_DIR" --quiet

# Copy handler
cp lambda/handler.py "$PKG_DIR/handler.py"

echo "==> Zipping deployment package..."
LAMBDA_ZIP="/tmp/lambda_package.zip"
(cd "$PKG_DIR" && zip -r "$LAMBDA_ZIP" . -x "*.pyc" -x "*/__pycache__/*" -q)
echo "    Package size: $(du -sh "$LAMBDA_ZIP" | cut -f1)"

# ── Step 3: Ensure IAM role exists ────────────────────────────────────────────
echo "==> Checking IAM role ${LAMBDA_ROLE_NAME}..."
ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE_NAME" \
    --query "Role.Arn" --output text 2>/dev/null || true)

if [[ -z "$ROLE_ARN" ]]; then
    echo "    Creating IAM role..."
    TRUST_POLICY='{
      "Version":"2012-10-17",
      "Statement":[{
        "Effect":"Allow",
        "Principal":{"Service":"lambda.amazonaws.com"},
        "Action":"sts:AssumeRole"
      }]
    }'
    ROLE_ARN=$(aws iam create-role \
        --role-name "$LAMBDA_ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --query "Role.Arn" --output text)
    aws iam attach-role-policy \
        --role-name "$LAMBDA_ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy \
        --role-name "$LAMBDA_ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
    echo "    Waiting for role to propagate..."
    sleep 15
fi
echo "    Role ARN: ${ROLE_ARN}"

# ── Step 4: Create or update Lambda function ──────────────────────────────────
ENV_VARS="Variables={GOOGLE_API_KEY=${GOOGLE_API_KEY},S3_BUCKET=${S3_BUCKET},S3_PREFIX=${S3_PREFIX}}"

EXISTING=$(aws lambda get-function --function-name "$LAMBDA_FUNCTION" \
    --region "$REGION" --query "Configuration.FunctionArn" --output text 2>/dev/null || true)

if [[ -z "$EXISTING" ]]; then
    echo "==> Creating Lambda function ${LAMBDA_FUNCTION}..."
    LAMBDA_ARN=$(aws lambda create-function \
        --function-name "$LAMBDA_FUNCTION" \
        --runtime python3.12 \
        --role "$ROLE_ARN" \
        --handler handler.handler \
        --zip-file "fileb://${LAMBDA_ZIP}" \
        --timeout 60 \
        --memory-size 1024 \
        --environment "$ENV_VARS" \
        --region "$REGION" \
        --query "FunctionArn" --output text)
else
    echo "==> Updating Lambda function ${LAMBDA_FUNCTION}..."
    aws lambda update-function-code \
        --function-name "$LAMBDA_FUNCTION" \
        --zip-file "fileb://${LAMBDA_ZIP}" \
        --region "$REGION" --output text > /dev/null
    aws lambda wait function-updated \
        --function-name "$LAMBDA_FUNCTION" \
        --region "$REGION"
    aws lambda update-function-configuration \
        --function-name "$LAMBDA_FUNCTION" \
        --timeout 60 \
        --memory-size 1024 \
        --environment "$ENV_VARS" \
        --region "$REGION" --output text > /dev/null
    LAMBDA_ARN="$EXISTING"
fi
echo "    Lambda ARN: ${LAMBDA_ARN}"

# ── Step 5: Create or reuse HTTP API Gateway ──────────────────────────────────
echo "==> Checking API Gateway (${API_NAME})..."
API_ID=$(aws apigatewayv2 get-apis --region "$REGION" \
    --query "Items[?Name=='${API_NAME}'].ApiId" --output text 2>/dev/null || true)

if [[ -z "$API_ID" ]]; then
    echo "    Creating HTTP API..."
    API_ID=$(aws apigatewayv2 create-api \
        --name "$API_NAME" \
        --protocol-type HTTP \
        --region "$REGION" \
        --query "ApiId" --output text)

    # Lambda integration
    INTEGRATION_ID=$(aws apigatewayv2 create-integration \
        --api-id "$API_ID" \
        --integration-type AWS_PROXY \
        --integration-uri "$LAMBDA_ARN" \
        --payload-format-version "2.0" \
        --region "$REGION" \
        --query "IntegrationId" --output text)

    # POST /query route
    aws apigatewayv2 create-route \
        --api-id "$API_ID" \
        --route-key "POST /query" \
        --target "integrations/${INTEGRATION_ID}" \
        --region "$REGION" --output text > /dev/null

    # $default stage with auto-deploy
    aws apigatewayv2 create-stage \
        --api-id "$API_ID" \
        --stage-name '$default' \
        --auto-deploy \
        --region "$REGION" --output text > /dev/null

    # Grant API Gateway permission to invoke Lambda
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    aws lambda add-permission \
        --function-name "$LAMBDA_FUNCTION" \
        --statement-id "apigateway-invoke" \
        --action "lambda:InvokeFunction" \
        --principal "apigateway.amazonaws.com" \
        --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*/query" \
        --region "$REGION" --output text > /dev/null
fi

ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/query"
echo ""
echo "=========================================="
echo " Deployment complete!"
echo " API endpoint: ${ENDPOINT}"
echo ""
echo " Set this in your Streamlit environment:"
echo "   export RAG_API_URL=\"${ENDPOINT}\""
echo "   # or add to .env / Streamlit secrets"
echo "=========================================="
