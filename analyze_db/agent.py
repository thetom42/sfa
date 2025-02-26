"""
This script defines an SQLite Agent that leverages the OpenAI API to generate and execute SQL queries.

The agent interacts with a SQLite database based on user requests, using OpenAI's function calling capabilities
to determine the appropriate actions to take, such as listing tables, describing table schemas,
sampling table data, and running SQL queries. The script includes functions for setting up the agent,
defining the OpenAI tools, and executing the main agent loop.
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
from typing import List
from rich.console import Console
from rich.panel import Panel
import dotenv
from dataclasses import dataclass


from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from fastapi import FastAPI, HTTPException
import uvicorn


dotenv.load_dotenv()
console = Console() # Initialize rich console


@dataclass
class Deps:
    db_path: str


_db_path = ''

# Create Agent instance
agent = Agent(
    name='Analyze DB Agent',
    model=OpenAIModel(
        "qwen2.5-14b-instruct-1m@6bit",
        base_url="http://localhost:1234/v1",
    ),
    deps_type=Deps
)


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
        conn = sqlite3.connect(ctx.deps.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        console.log(f"[blue]List Tables Tool[/blue] - Reasoning: {reasoning}")
        return tables
    except Exception as e:
        console.log(f"[red]Error listing tables: {str(e)}[/red]")
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
        conn = sqlite3.connect(ctx.deps.db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info('{table_name}');")
        rows = cursor.fetchall()
        conn.close()
        output = "\\n".join([str(row) for row in rows])
        console.log(f"[blue]Describe Table Tool[/blue] - Table: {table_name} - Reasoning: {reasoning}")
        return output
    except Exception as e:
        console.log(f"[red]Error describing table: {str(e)}[/red]")
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
        conn = sqlite3.connect(ctx.deps.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {row_sample_size};")
        rows = cursor.fetchall()
        conn.close()
        output = "\\n".join([str(row) for row in rows])
        console.log(
            f"[blue]Sample Table Tool[/blue] - Table: {table_name} - Rows: {row_sample_size} - Reasoning: {reasoning}"
        )
        return output
    except Exception as e:
        console.log(f"[red]Error sampling table: {str(e)}[/red]")
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
        conn = sqlite3.connect(ctx.deps.db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.commit()
        conn.close()
        output = "\\n".join([str(row) for row in rows])
        console.log(f"[blue]Test Query Tool[/blue] - Reasoning: {reasoning}")
        console.log(f"[dim]Query: {sql_query}[/dim]")
        return output
    except Exception as e:
        console.log(f"[red]Error running test query: {str(e)}[/red]")
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
        conn = sqlite3.connect(ctx.deps.db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.commit()
        conn.close()
        output = "\\n".join([str(row) for row in rows])
        console.log(
            Panel(
                f"[green]Final Query Tool[/green]\\nReasoning: {reasoning}\\nQuery: {sql_query}"
            )
        )
        return output
    except Exception as e:
        console.log(f"[red]Error running final query: {str(e)}[/red]")
        return str(e)


async def run_agent(prompt: str):
    """
    Runs the SQLite agent with the given parameters.
    """
    deps = Deps(
        db_path=_db_path
    )

    console.rule(
        "[yellow]Agent Loop[/yellow]"
    )

    try:
        result = await agent.run(prompt, deps=deps)
        console.print("\n[green]Final Results:[/green]")
        console.print(result.data)
        return result.data

    except Exception as e:
        console.print(f"[red]Error in agent loop: {str(e)}[/red]")
        raise e


app = FastAPI()


@app.get("/run")
async def run(prompt: str):
    try:
        result = await run_agent(prompt)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def setup_parser():
    """
    Sets up the argument parser.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description="SQLite Agent")

    parser.add_argument(
        "-d", "--db", required=True, help="Path to SQLite database file"
    )

    args = parser.parse_args()

    return args


def main():
   """
   Main function to set up and run the SQLite agent.
   """
   args = setup_parser()

   global _db_path
   _db_path = args.db

   uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
   main()
