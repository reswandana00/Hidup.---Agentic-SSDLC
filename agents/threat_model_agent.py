"""
Threat Model Agent for creating comprehensive threat models.
Identifies and analyzes security threats with risk analysis.
"""
from pydantic_ai import Agent
from .models import ThreatModel
from .utils import user_input_tool


def create_threat_model_agent(model, memory_tools):
    """Create agent for Threat Model."""
    threat_model_prompt = """
    You are a security analyst creating 'ThreatModel' documentation.

    Process:
    1. **Use `list_available_documents_tool` to see all available documents**
    2. **Use `read_document_tool` to read 'system_design' and 'system_architecture'** as main sources
    3. Based on this information, identify potential threats with:
        - Unique threat ID
        - Clear threat name and description
        - Target assets
        - Risk analysis (0-10 for each factor: damage, reproducibility, exploitability, affected users, discoverability)
        - Practical mitigations
    4. If you need input about specific threat scenarios, use 'user_input_tool' to ask (one question at a time)
    5. Ensure each threat has realistic risk analysis and practical mitigations
    6. Ensure final output follows 'ThreatModel' schema exactly
    """
    return Agent(
        model=model, 
        system_prompt=threat_model_prompt, 
        output_type=ThreatModel, 
        tools=[user_input_tool] + memory_tools
    )
