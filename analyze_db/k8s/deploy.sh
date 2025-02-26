#!/bin/bash
# Script to build and deploy the SQLite Agent to Kubernetes

set -e  # Exit on error

# Configuration
IMAGE_NAME="sqlite-agent"
IMAGE_TAG="latest"
REGISTRY=""  # Set to your registry if using one, e.g., "gcr.io/your-project/"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --registry)
      REGISTRY="$2/"
      shift
      shift
      ;;
    --tag)
      IMAGE_TAG="$2"
      shift
      shift
      ;;
    --namespace)
      NAMESPACE="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set the full image name
FULL_IMAGE_NAME="${REGISTRY}${IMAGE_NAME}:${IMAGE_TAG}"

# Build the Docker image
echo "Building Docker image: ${FULL_IMAGE_NAME}"
docker build -t "${FULL_IMAGE_NAME}" -f ../Dockerfile ..

# Push the image if a registry is specified
if [ -n "$REGISTRY" ]; then
  echo "Pushing image to registry: ${FULL_IMAGE_NAME}"
  docker push "${FULL_IMAGE_NAME}"
fi

# Update the image in the deployment.yaml file
echo "Updating deployment.yaml with image: ${FULL_IMAGE_NAME}"
sed -i.bak "s|image: sqlite-agent:latest|image: ${FULL_IMAGE_NAME}|g" deployment.yaml
rm -f deployment.yaml.bak

# Create namespace if specified and doesn't exist
if [ -n "$NAMESPACE" ]; then
  if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
  fi
  NAMESPACE_ARG="--namespace $NAMESPACE"
else
  NAMESPACE_ARG=""
fi

# Deploy to Kubernetes using kustomize
echo "Deploying to Kubernetes"
kubectl apply -k . $NAMESPACE_ARG

echo "Deployment completed successfully!"
echo "To check the status of your deployment, run:"
if [ -n "$NAMESPACE" ]; then
  echo "kubectl get pods -n $NAMESPACE -l app=sqlite-agent"
else
  echo "kubectl get pods -l app=sqlite-agent"
fi