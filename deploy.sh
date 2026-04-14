#!/bin/bash

# Metis Intelligence: Secure Deployment Script (XXXX)
# ------------------------------

# 1. Set variables
PROJECT_ID="XXXX"
REGION="us-central1"
SERVICE_NAME="metis-prototype"

# Ask for the user's personal Google email for delegation
read -p "Enter your personal Google email (for authentication delegation): " USER_EMAIL

echo "Deploying Metis Intelligence to project: $PROJECT_ID in region: $REGION"

# 2. Enable necessary APIs
echo "Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com

# 3. Submit build to Cloud Build
echo "Building and pushing container..."
gcloud builds submit --config cloudbuild.yaml .

# 4. Deploy to Cloud Run (Securely)
echo "Deploying to Cloud Run with IAM authentication..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/metis-prototype \
    --region $REGION \
    --platform managed \
    --no-allow-unauthenticated \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION"

# 5. Delegate Identity (Grant Invoker Role)
echo "Granting 'roles/run.invoker' to $USER_EMAIL..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member="user:$USER_EMAIL" \
    --role="roles/run.invoker" \
    --region=$REGION

# 6. Success message
echo "--------------------------------------------------"
echo "Metis Intelligence Deployment complete and secured!"
echo "Your Metis API is now private to: $USER_EMAIL"
echo ""
echo "To call your API for a demo, use this command to get a token:"
echo "export TOKEN=\$(gcloud auth print-identity-token)"
echo "curl -X POST \"\$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')/research\" \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"domain_id\": \"7\"}'"
echo "--------------------------------------------------"
