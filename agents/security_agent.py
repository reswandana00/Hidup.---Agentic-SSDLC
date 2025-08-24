"""
Security Requirements Agent for creating security-relevant requirements.
Analyzes system context to identify security requirements and user roles.
"""
from pydantic_ai import Agent
from .models import SecurityRequirements
from .utils import user_input_tool


def create_security_requirement_agent(model, memory_tools):
    """Create agent for Security Requirements."""
    security_prompt = """
    You are a security analyst creating 'SecurityRequirements' documentation.

    Process:
    1. **Use `list_available_documents_tool` to see all documents in memory**
    2. **Use `read_document_tool` to read relevant documents** like 'interview_results' and 'environment_requirements'
    3. Identify user roles, threat actors, security controls, and data protection needs
    4. If you need specific details (e.g., company security policies), use 'user_input_tool' to ask. ONE question at a time
    5. If user doesn't know, create standard answers based on application security best practices
    6. Ensure final output follows 'SecurityRequirements' schema exactly
    """
    return Agent(
        model=model, 
        system_prompt=security_prompt, 
        output_type=SecurityRequirements, 
        tools=[user_input_tool] + memory_tools
    )
