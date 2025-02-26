# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables
ENV MODEL_NAME="qwen2.5-14b-instruct-1m@6bit"
ENV MODEL_BASE_URL="http://localhost:1234/v1"
ENV DB_PATH="/data/database.sqlite"

# Create a volume mount point for the database
VOLUME ["/data"]

# Run the application when the container launches
CMD ["python", "agent_improved.py", "--api", "--db", "${DB_PATH}"]