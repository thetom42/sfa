# Deploying SQLite Agent to Kubernetes

This directory contains Kubernetes configuration files for deploying the SQLite Agent as a REST API application.

## Prerequisites

- Docker installed on your local machine
- Access to a Kubernetes cluster
- `kubectl` configured to communicate with your cluster
- (Optional) Ingress controller installed in your cluster for external access

## Deployment Steps

### 1. Build the Docker Image

From the root directory of the project:

```bash
docker build -t sqlite-agent:latest -f Dockerfile .
```

If you're using a remote container registry (e.g., Docker Hub, Google Container Registry), tag and push the image:

```bash
docker tag sqlite-agent:latest your-registry/sqlite-agent:latest
docker push your-registry/sqlite-agent:latest
```

Then update the `image` field in `deployment.yaml` to match your registry path.

### 2. Prepare Your Database

You have two options for the database:

#### Option A: Use a Persistent Volume (Recommended for Production)

The default configuration uses a PersistentVolumeClaim to store the SQLite database file. This ensures data persistence across pod restarts.

#### Option B: Pre-populate a Database in the Image (For Testing Only)

For testing or when using a read-only database, you can include the database file in the Docker image. Modify the Dockerfile to copy your database file:

```dockerfile
# Add this line to the Dockerfile
COPY your-database.sqlite /data/database.sqlite
```

### 3. Configure the Application

Review and modify the ConfigMap in `configmap.yaml` to set the appropriate values for:

- `model_name`: The name of the model to use
- `model_base_url`: The base URL for the model API

### 4. Deploy to Kubernetes

Apply the Kubernetes configurations in the following order:

```bash
# Create namespace (optional)
kubectl create namespace sqlite-agent

# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Apply ingress (optional, for external access)
kubectl apply -f k8s/ingress.yaml
```

### 5. Verify the Deployment

Check if the pods are running:

```bash
kubectl get pods -l app=sqlite-agent
```

Check the service:

```bash
kubectl get svc sqlite-agent
```

### 6. Access the API

#### Internal Access (within the cluster)

Other services within the cluster can access the API at:

```
http://sqlite-agent/run?prompt=your-prompt-here
```

#### External Access (if using Ingress)

If you've configured the Ingress, you can access the API at:

```
http://sqlite-agent.example.com/run?prompt=your-prompt-here
```

Replace `sqlite-agent.example.com` with your actual domain.

## Scaling Considerations

SQLite is a file-based database that doesn't support multiple concurrent writers. Therefore, the deployment is configured with `replicas: 1`. If you need to scale the application:

1. Consider using a database that supports concurrent access (e.g., PostgreSQL, MySQL)
2. Modify the application to use the new database
3. Update the Kubernetes configurations accordingly

## Monitoring and Logging

The application includes health check endpoints:

- `/healthz/live`: Liveness probe to check if the application is running
- `/healthz/ready`: Readiness probe to check if the database connection is working

These endpoints are used by Kubernetes to monitor the health of the application.

For logging, consider integrating with a centralized logging system (e.g., ELK stack, Loki).