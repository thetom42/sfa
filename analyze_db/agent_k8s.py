"""
This script defines an SQLite Agent that leverages the OpenAI API to generate and execute SQL queries.

The agent interacts with a SQLite database based on user requests, using OpenAI's function calling capabilities
to determine the appropriate actions to take, such as listing tables, describing table schemas,
sampling table data, and running SQL queries. The script includes functions for setting up the agent,
defining the OpenAI tools, and executing the main agent loop.

This version is adapted for Kubernetes deployment with health check endpoints and environment variable configuration.
"""
# /// script
# dependencies = [
#   "rich",
#   "python-dotenv",
#   "pydantic_ai",
#   "fastapi[standard]",
#   "uvicorn"
# ]
# ///

import argparse
import sqlite3
import asyncio
import os
from typing import List
from rich.console import Console
from rich.panel import Panel
import dotenv
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()


@dataclass
class Deps:
    """Dependencies for the agent."""
    db_path: str


@dataclass
class AgentConfig:
    """Configuration for the agent."""
    db_path: str
    model_name: str = None
    base_url: str = None
    api_mode: bool = False
    
    def __post_init__(self):
        """Initialize with environment variables if not provided."""
        if self.model_name is None:
            self.model_name = os.environ.get("MODEL_NAME", "qwen2.5-14b-instruct-1m@6bit")
        if self.base_url is None:
            self.base_url = os.environ.get("MODEL_BASE_URL", "http://localhost:1234/v1")


class DatabaseManager:
    """Handles all database operations."""
    def __init__(self, db_path):
        self.db_path = db_path
        
    def connect(self):
        """Create and return a database connection."""
        return sqlite3.connect(self.db_path)
        
    def list_tables(self):
        """Returns a list of tables in the database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
        
    def describe_table(self, table_name):
        """Returns schema information about the specified table."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        rows = cursor.fetchall()
        conn.close()
        return rows
        
    def sample_table(self, table_name, row_sample_size):
        """Returns a sample of rows from the specified table."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {row_sample_size};")
        rows = cursor.fetchall()
        conn.close()
        return rows
        
    def execute_query(self, sql_query):
        """Executes an SQL query and returns results."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.commit()
        conn.close()
        return rows
    
    def check_connection(self) -> bool:
        """Check if the database connection is working."""
        try:
            conn = self.connect()
            conn.close()
            return True
        except Exception:
            return False


class Logger:
    """Handles all logging operations."""
    def __init__(self):
        self.console = Console()
        
    def log_tool_execution(self, tool_name, details, error=None):
        """Log tool execution with details."""
        if error:
            self.console.log(f"[red]Error {tool_name}: {str(error)}[/red]")
        else:
            self.console.log(f"[blue]{tool_name}[/blue] - {details}")
            
    def log_final_query(self, reasoning, sql_query):
        """Log the final query execution."""
        self.console.log(
            Panel(
                f"[green]Final Query Tool[/green]\nReasoning: {reasoning}\nQuery: {sql_query}"
            )
        )
        
    def log_result(self, result):
        """Log the final result."""
        self.console.print("\n[green]Final Results:[/green]")
        self.console.print(result)
        
    def rule(self, title):
        """Add a rule with title."""
        self.console.rule(title)


class SQLiteAgent:
    """Main agent class that coordinates all operations."""
    def __init__(self, config):
        self.config = config
        self.logger = Logger()
        self.db_manager = DatabaseManager(config.db_path)
        self.agent = self._create_agent()
        
    def _create_agent(self):
        """Create and configure the agent with tools."""
        agent = Agent(
            name='Analyze DB Agent',
            model=OpenAIModel(
                self.config.model_name,
                base_url=self.config.base_url,
            ),
            deps_type=Deps
        )
        
        # Register system prompt
        @agent.system_prompt 
        async def system_prompt() -> str:
            """Generates the system prompt for the OpenAI API based on user input.

                Returns:
                The system prompt to be used by the OpenAI API
            """
            return """
                <purpose>
                    You are a world-class expert at crafting precise SQLite SQL queries.
                    Your goal is to generate accurate queries that exactly match the user's data needs.
                </purpose>
                
                <instructions>
                    <instruction>Use the provided tools to explore the database and construct the perfect query.</instruction>
                    <instruction>Start by listing tables to understand what's available.</instruction>
                    <instruction>Describe tables to understand their schema and columns.</instruction>
                    <instruction>Sample tables to see actual data patterns.</instruction>
                    <instruction>Test queries before finalizing them.</instruction>
                    <instruction>Only call run_final_sql_query when you're confident the query is perfect.</instruction>
                    <instruction>Be thorough but efficient with tool usage.</instruction>
                    <instruction>If you find your run_test_sql_query tool call returns an error or won't satisfy the user request, try to fix the query or try a different query.</instruction>
                    <instruction>Think step by step about what information you need.</instruction>
                    <instruction>Be sure to specify every parameter for each tool call.</instruction>
                    <instruction>Every tool call should have a reasoning parameter which gives you a place to explain why you are calling the tool.</instruction>
                </instructions>
                
                <user-request>
                    {{user_request}}
                </user-request>
            """
        
        # Register tools
        self._register_tools(agent)
        
        return agent
    
    def _register_tools(self, agent):
        """Register all tools for the agent."""
        db_manager = self.db_manager
        logger = self.logger
        
        @agent.tool
        async def list_tables(ctx: RunContext[Deps], reasoning: str) -> List[str]:
            """Returns a list of tables in the database.

            The agent uses this to discover available tables and make informed decisions.

            Args:
                reasoning: Explanation of why we're listing tables relative to user request

            Returns:
                List of table names as strings
            """
            try:
                tables = db_manager.list_tables()
                logger.log_tool_execution("List Tables Tool", f"Reasoning: {reasoning}")
                return tables
            except Exception as e:
                logger.log_tool_execution("List Tables Tool", None, error=e)
                return []
                
        @agent.tool
        async def describe_table(ctx: RunContext[Deps], reasoning: str, table_name: str) -> str:
            """Returns schema information about the specified table.

            The agent uses this to understand table structure and available columns.

            Args:
                reasoning: Explanation of why we're describing this table
                table_name: Name of table to describe

            Returns:
                String containing table schema information
            """
            try:
                rows = db_manager.describe_table(table_name)
                output = "\n".join([str(row) for row in rows])
                logger.log_tool_execution("Describe Table Tool", f"Table: {table_name} - Reasoning: {reasoning}")
                return output
            except Exception as e:
                logger.log_tool_execution("Describe Table Tool", None, error=e)
                return ""
                
        @agent.tool
        async def sample_table(ctx: RunContext[Deps], reasoning: str, table_name: str, row_sample_size: int) -> str:
            """Returns a sample of rows from the specified table.

            The agent uses this to understand actual data content and patterns.

            Args:
                reasoning: Explanation of why we're sampling this table
                table_name: Name of table to sample from
                row_sample_size: Number of rows to sample aim for 3-5 rows

            Returns:
                String containing sample rows in readable format
            """
            try:
                rows = db_manager.sample_table(table_name, row_sample_size)
                output = "\n".join([str(row) for row in rows])
                logger.log_tool_execution(
                    "Sample Table Tool", 
                    f"Table: {table_name} - Rows: {row_sample_size} - Reasoning: {reasoning}"
                )
                return output
            except Exception as e:
                logger.log_tool_execution("Sample Table Tool", None, error=e)
                return ""
                
        @agent.tool
        async def run_test_sql_query(ctx: RunContext[Deps], reasoning: str, sql_query: str) -> str:
            """Executes a test SQL query and returns results.

            The agent uses this to validate queries before finalizing them.
            Results are only shown to the agent, not the user.

            Args:
                reasoning: Explanation of why we're running this test query
                sql_query: The SQL query to test

            Returns:
                Query results as a string
            """
            try:
                rows = db_manager.execute_query(sql_query)
                output = "\n".join([str(row) for row in rows])
                logger.log_tool_execution("Test Query Tool", f"Reasoning: {reasoning}")
                logger.console.log(f"[dim]Query: {sql_query}[/dim]")
                return output
            except Exception as e:
                logger.log_tool_execution("Test Query Tool", None, error=e)
                return str(e)
                
        @agent.tool
        async def run_final_sql_query(ctx: RunContext[Deps], reasoning: str, sql_query: str) -> str:
            """Executes the final SQL query and returns results to user.

            This is the last tool call the agent should make after validating the query.

            Args:
                reasoning: Final explanation of how this query satisfies user request
                sql_query: The validated SQL query to run

            Returns:
                Query results as a string
            """
            try:
                rows = db_manager.execute_query(sql_query)
                output = "\n".join([str(row) for row in rows])
                logger.log_final_query(reasoning, sql_query)
                return output
            except Exception as e:
                logger.log_tool_execution("Final Query Tool", None, error=e)
                return str(e)
        
    async def run(self, prompt):
        """Run the agent with the given prompt."""
        deps = Deps(db_path=self.config.db_path)
        
        self.logger.rule("[yellow]Agent Loop[/yellow]")
        
        try:
            result = await self.agent.run(prompt, deps=deps)
            self.logger.log_result(result.data)
            return result.data
        except Exception as e:
            self.logger.console.print(f"[red]Error in agent loop: {str(e)}[/red]")
            raise e


def create_app(db_path):
    """Create a FastAPI app with the agent."""
    app = FastAPI(
        title="SQLite Agent API",
        description="API for running SQL queries against a SQLite database using an AI agent",
        version="1.0.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
    # Create a single agent instance to be reused across requests
    config = AgentConfig(db_path=db_path)
    agent = SQLiteAgent(config)
    db_manager = agent.db_manager
    
    @app.get("/run")
    async def run(prompt: str):
        """API endpoint to run the agent with a prompt."""
        try:
            result = await agent.run(prompt)
            return {"result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/healthz/live")
    async def liveness_probe():
        """Kubernetes liveness probe endpoint.
        
        This endpoint is used by Kubernetes to determine if the application is running.
        It always returns a 200 OK status code.
        """
        return {"status": "alive"}
    
    @app.get("/healthz/ready")
    async def readiness_probe():
        """Kubernetes readiness probe endpoint.
        
        This endpoint is used by Kubernetes to determine if the application is ready to serve traffic.
        It checks if the database connection is working.
        """
        if db_manager.check_connection():
            return {"status": "ready"}
        else:
            return Response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content="Database connection failed"
            )
    
    @app.get("/")
    async def root():
        """Root endpoint that provides basic information about the API."""
        return {
            "name": "SQLite Agent API",
            "version": "1.0.0",
            "endpoints": {
                "/run": "Run the agent with a prompt",
                "/healthz/live": "Kubernetes liveness probe",
                "/healthz/ready": "Kubernetes readiness probe"
            }
        }
            
    return app


def setup_parser():
    """Sets up the argument parser."""
    parser = argparse.ArgumentParser(description="SQLite Agent")
    
    parser.add_argument(
        "-d", "--db", required=True, help="Path to SQLite database file"
    )
    parser.add_argument(
        "--api", action="store_true", help="Run as API server"
    )
    parser.add_argument(
        "-p", "--prompt", help="The user's request (required if not in API mode)"
    )
    
    args = parser.parse_args()
    
    if not args.api and not args.prompt:
        parser.error("--prompt is required when not in API mode")
    
    return args


def main():
    """Main function to set up and run the SQLite agent."""
    # Check for environment variables first
    db_path = os.environ.get("DB_PATH")
    
    # If not set in environment, use command line arguments
    if not db_path:
        args = setup_parser()
        db_path = args.db
        
        if args.api:
            import uvicorn
            app = create_app(db_path)
            uvicorn.run(app, host="0.0.0.0", port=8000)
        else:
            config = AgentConfig(db_path=db_path)
            agent = SQLiteAgent(config)
            asyncio.run(agent.run(args.prompt))
    else:
        # If DB_PATH is set in environment, assume we're running in API mode
        import uvicorn
        app = create_app(db_path)
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()