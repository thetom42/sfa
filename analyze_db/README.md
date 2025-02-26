# SQLite Agent

This directory contains a Python application that leverages the OpenAI API to generate and execute SQL queries against a SQLite database. The agent interacts with the database based on user requests, using OpenAI's function calling capabilities to determine the appropriate actions to take.

## Files in this Directory

### `agent_improved.py`

The original implementation of the SQLite Agent. This script:

- Defines an agent that can interact with a SQLite database
- Uses OpenAI's function calling capabilities to generate and execute SQL queries
- Provides tools for listing tables, describing table schemas, sampling table data, and running SQL queries
- Can be run as a command-line application or as a FastAPI server

Usage:
```bash
# Run as a command-line application
python agent_improved.py --db path/to/database.sqlite --prompt "Your query request here"

# Run as an API server
python agent_improved.py --db path/to/database.sqlite --api
```

### `agent_k8s.py`

A Kubernetes-ready version of the SQLite Agent. This script extends `agent_improved.py` with:

- Health check endpoints for Kubernetes liveness and readiness probes
- Environment variable configuration for containerized deployment
- Enhanced error handling and logging
- CORS middleware for the FastAPI application
- A more robust database connection check

Usage:
```bash
# Run as a command-line application
python agent_k8s.py --db path/to/database.sqlite --prompt "Your query request here"

# Run as an API server
python agent_k8s.py --db path/to/database.sqlite --api

# Run with environment variables
DB_PATH=/path/to/database.sqlite MODEL_NAME=your-model MODEL_BASE_URL=your-url python agent_k8s.py --api
```

### `Dockerfile`

A Dockerfile for containerizing the SQLite Agent. This file:

- Uses Python 3.9 as the base image
- Installs the required dependencies
- Copies the application code into the container
- Sets up environment variables
- Exposes port 8000 for the FastAPI server
- Creates a volume mount point for the database
- Defines the command to run the application

Usage:
```bash
# Build the Docker image
docker build -t sqlite-agent:latest .

# Run the Docker container
docker run -p 8000:8000 -v /path/to/your/data:/data sqlite-agent:latest
```

### `deployment_plan.md`

A document outlining the steps to deploy the SQLite Agent as a REST API application on Kubernetes. This file covers:

1. Review of the existing FastAPI implementation
2. Addition of health check endpoints
3. Containerization with Docker
4. Kubernetes deployment files
5. Configuration management
6. Resource limits
7. External access options
8. Error handling and logging improvements

## Kubernetes Deployment

The `k8s` directory contains Kubernetes configuration files for deploying the SQLite Agent to a Kubernetes cluster. See the README.md file in that directory for detailed deployment instructions.

## Dependencies

The application requires the following Python packages:

- rich
- python-dotenv
- pydantic_ai
- fastapi[standard]
- uvicorn

These dependencies are listed in the script comments and should be installed before running the application.