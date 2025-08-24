"""
Environment Agent for creating operational environment specifications.
Analyzes interview data to create environment requirements.
"""
from pydantic_ai import Agent
from .models import EnvironmentRequirements
from .utils import user_input_tool


def create_environment_agent(model, memory_tools):
    """Create agent for Environment Requirements."""
    environment_prompt = """
    You are a systems analyst creating 'EnvironmentRequirements' documentation.
    
    Process:
    1. **Use `read_document_tool` to read 'interview_results'** as your main information source
    2. Based on interview data, create environment specifications
    3. If information is unclear or too specific (e.g., exact OS versions, user permissions), use 'user_input_tool' to ask user
    4. **CRITICAL: Ask ONLY ONE question at a time.** Wait for response before continuing
    5. If user doesn't know, create safe, standard answers for the application type
    6. Ensure final output follows 'EnvironmentRequirements' schema exactly
    """
    return Agent(
        model=model, 
        system_prompt=environment_prompt, 
        output_type=EnvironmentRequirements, 
        tools=[user_input_tool] + memory_tools
    )
