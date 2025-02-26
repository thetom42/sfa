# SQLite Agent

This directory contains a Python application that leverages the Pydantic AI framework to generate and execute SQL queries against a SQLite database. The agent interacts with the database based on user requests.

## Files in this Directory

### `agent.py`

This script defines an SQLite Agent that interacts with a SQLite database using the Pydantic AI framework. It can list tables, describe schemas, sample data, and run SQL queries based on user requests. The agent provides tools using the `agent.tool` decorator. The agent is a REST API.

- Defines an agent that can interact with a SQLite database
- Uses the Pydantic AI framework to generate and execute SQL queries
- Provides tools using the `agent.tool` decorator for listing tables, describing table schemas, sampling table data, and running SQL queries
- Runs as a FastAPI server

Usage:

```bash
uv run agent.py --db path/to/database.sqlite
```

### `agent_improved.py`

This is an improved version of the agent that adheres to principles like "Seperation of Concerns" and "Information Hiding":

- Provides the same features as 'agent.py
- Separates database management, logging, configuration and the agent itself by using different classes
- Can be run as a command-line application or as a FastAPI server

Usage:

```bash
# Run as a command-line application
uv run agent_improved.py --db path/to/database.sqlite --prompt "Your query request here"

# Run as an API server
uv run agent_improved.py --db path/to/database.sqlite --api
```

### `agent_k8s.py`

A Kubernetes-ready version of the SQLite Agent. This script extends `agent_improved.py`. It adds:

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

## Kubernetes Deployment

The `k8s` directory contains Kubernetes configuration files for deploying the SQLite Agent to a Kubernetes cluster. See the README.md file in that directory for detailed deployment instructions.

## Dependencies

The application requires the following Python packages which are automatically resolved when using 'uv run' to start the application. All scripts use uv's [inline metadata](https://docs.astral.sh/uv/guides/scripts/#running-a-script-with-dependencies) format for specifying the dependencies:

- rich
- python-dotenv
- pydantic_ai
- fastapi[standard]
- uvicorn
