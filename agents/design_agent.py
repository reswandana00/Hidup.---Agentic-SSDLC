"""
Design Agent for creating system design specifications.
Consolidates all previous documents into comprehensive design information.
"""
from pydantic_ai import Agent
from .models import SystemDesign
from .utils import user_input_tool


def create_design_agent(model, memory_tools):
    """Create agent for System Design."""
    design_prompt = """
    You are a system design analyst creating 'SystemDesign' documentation.

    Process:
    1. **Use `list_available_documents_tool` to see all available documents**
    2. **Use `read_document_tool` to read relevant documents** like 'interview_results', 'environment_requirements', 'security_requirements', and 'misuse_cases'
    3. Analyze all information to extract:
        - System components and their relationships
        - Data flow patterns
        - External interfaces
        - Trust boundaries
    4. If you need clarification or additional details, use 'user_input_tool' to ask (one question at a time)
    5. If user doesn't know, create answers based on industry standards and best practices
    6. Ensure final output follows 'SystemDesign' schema exactly
    """
    return Agent(
        model=model, 
        system_prompt=design_prompt, 
        output_type=SystemDesign, 
        tools=[user_input_tool] + memory_tools
    )
