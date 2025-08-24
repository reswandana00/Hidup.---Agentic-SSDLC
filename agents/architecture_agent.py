"""
Architecture Agent for creating system architecture specifications.
Transforms design information into architectural components and security zones.
"""
from pydantic_ai import Agent
from .models import SystemArchitecture
from .utils import user_input_tool


def create_architecture_agent(model, memory_tools):
    """Create agent for System Architecture."""
    architecture_prompt = """
    You are a system architect creating 'SystemArchitecture' documentation.

    Process:
    1. **Use `list_available_documents_tool` to see all available documents**
    2. **Use `read_document_tool` to read 'system_design'** as your main source
    3. Based on design information, create:
        - Architectural overview and description
        - Key components and their relationships
        - Security zones and boundaries
        - Attack surfaces and entry points
    4. If you need additional architectural details, use 'user_input_tool' to ask (one question at a time)
    5. Ensure all components have logical security zones
    6. Ensure final output follows 'SystemArchitecture' schema exactly
    """
    return Agent(
        model=model, 
        system_prompt=architecture_prompt, 
        output_type=SystemArchitecture, 
        tools=[user_input_tool] + memory_tools
    )
