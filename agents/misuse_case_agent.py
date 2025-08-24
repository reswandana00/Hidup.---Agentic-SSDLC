"""
Misuse Case Agent for creating misuse case scenarios.
Identifies potential abuse cases and security threats.
"""
from pydantic_ai import Agent
from .models import MisuseCases
from .utils import user_input_tool


def create_misuse_case_agent(model, memory_tools):
    """Create agent for Misuse Cases."""
    misuse_case_prompt = """
    You are a security analyst creating 'MisuseCases' documentation.

    Process:
    1. **Use `list_available_documents_tool` to check all created documents**
    2. **Use `read_document_tool` to read 'security_requirements'** document - contains threat profiles and user roles essential for your task
    3. Based on this context, create detailed and relevant misuse cases for the application
    4. If you need to discuss other attack scenarios, use 'user_input_tool' to ask user (one question at a time)
    5. If user has no input, create at least 3-5 most common and relevant misuse cases
    6. Ensure final output follows 'MisuseCases' schema exactly
    """
    return Agent(
        model=model, 
        system_prompt=misuse_case_prompt, 
        output_type=MisuseCases, 
        tools=[user_input_tool] + memory_tools
    )
