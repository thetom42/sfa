# Deployment Plan for SQLite Agent on Kubernetes

This document outlines the steps to deploy the SQLite agent (`analyze_db/agent_improved.py`) as a REST API application on Kubernetes.

## Steps

1.  **Review Existing FastAPI Implementation (DONE):** The script already includes a basic FastAPI implementation. We reviewed it and found it suitable as a starting point.

2.  **Add Health Check Endpoints:** Add `/healthz/live` and `/healthz/ready` endpoints to the FastAPI app for liveness and readiness probes. These are essential for Kubernetes to monitor the application's health.

    *   `/healthz/live`: Should return a 200 OK status code if the application is running. This is a simple check.
    *   `/healthz/ready`: Should return a 200 OK status code if the application is ready to serve traffic. This might involve checking the database connection.

3.  **Containerization (Dockerfile):** Create a `Dockerfile` to build a Docker image for the application. This file should:

    *   Use a suitable Python base image (e.g., `python:3.9-slim-buster`).
    *   Install necessary dependencies (using `pip` and the `requirements.txt` file, if present, or the dependencies listed in the script).
    *   Copy the application code into the image.
    *   Set environment variables (if needed).
    *   Define the command to run the application (using `uvicorn`).

4.  **Kubernetes Deployment Files (YAML):** Create Kubernetes YAML files to define the deployment:

    *   **Deployment:** Describes the desired state of the application (replicas, container image, resource limits, etc.).
    *   **Service:** Exposes the application within the cluster (using a `ClusterIP` service) or externally (using a `LoadBalancer` or `NodePort` service).
    *   **ConfigMap (Optional):**  For storing configuration values (e.g., database path) as environment variables.
    *   **Secrets (Optional):** For storing sensitive information (e.g., API keys) as environment variables.

5.  **Configuration Management:**

    *   Use environment variables for all configuration options (database path, model name, base URL, etc.).
    *   For the SQLite database, we have a few options:
        *   **Persistent Volume (PV) and Persistent Volume Claim (PVC):** Recommended for production, ensuring data persistence.
        *   **Embed the database in the Docker image (NOT RECOMMENDED for production):**  Suitable for testing only, as data will be lost on pod restarts.
        * **External Database (consider if appropriate):** If scaling is critical, moving to a more robust datastore is preferred.

6.  **Resource Limits:** Define resource requests and limits (CPU, memory) in the Kubernetes Deployment to prevent resource exhaustion.

7.  **External Access (Ingress - Optional):** If external access is required, configure an Ingress controller and Ingress resource.

8.  **Error Handling and Logging:** The current script has basic logging. Consider enhancing this for production, potentially integrating with a centralized logging system.