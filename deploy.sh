#!/bin/bash
# LawnRouter Deployment Script
# Deploys SAM stack and syncs static assets to S3/CloudFront

set -e

STACK_NAME="${STACK_NAME:-lawnrouter}"
REGION="${AWS_REGION:-us-east-1}"
MAPBOX_TOKEN="${MAPBOX_PUBLIC_TOKEN:-}"

echo "=== LawnRouter Deployment ==="
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Build SAM application
echo "Building SAM application..."
sam build

# Deploy SAM stack
echo ""
echo "Deploying SAM stack..."
sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "MapboxPublicToken=$MAPBOX_TOKEN" \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

# Get outputs
echo ""
echo "Fetching stack outputs..."
STATIC_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='StaticBucketName'].OutputValue" \
    --output text)

STATIC_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='StaticURL'].OutputValue" \
    --output text)

API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
    --output text)

echo "Static Bucket: $STATIC_BUCKET"
echo "Static URL: $STATIC_URL"
echo "API Endpoint: $API_ENDPOINT"

# Sync static assets to S3
if [ -d "static-build" ] && [ -n "$STATIC_BUCKET" ]; then
    echo ""
    echo "Syncing static assets to S3..."
    aws s3 sync static-build/ "s3://$STATIC_BUCKET/" \
        --delete \
        --cache-control "public,max-age=300" \
        --region "$REGION"

    echo "Static assets synced successfully!"
else
    echo ""
    echo "Warning: static-build directory not found or bucket not available"
fi

# Invalidate CloudFront cache (optional, for faster updates during development)
CDN_ID=$(aws cloudformation describe-stack-resource \
    --stack-name "$STACK_NAME" \
    --logical-resource-id StaticCDN \
    --region "$REGION" \
    --query "StackResourceDetail.PhysicalResourceId" \
    --output text 2>/dev/null || echo "")

if [ -n "$CDN_ID" ]; then
    echo ""
    echo "Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id "$CDN_ID" \
        --paths "/*" \
        --region "$REGION" > /dev/null
    echo "CloudFront invalidation created"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Dashboard URL: ${API_ENDPOINT}/dashboard?company_id=YOUR_COMPANY_ID"
echo "Static Assets: $STATIC_URL"
echo ""
