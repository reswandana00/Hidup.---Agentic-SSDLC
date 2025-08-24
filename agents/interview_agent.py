"""
Interview Agent for collecting initial requirements.
Conducts conversational interviews to gather business needs and specifications.
"""
from pydantic_ai import Agent
from .models import InterviewResults
from .utils import user_input_tool


def create_interview_agent(model):
    """Membuat agen untuk interview awal."""
    interview_prompt = """
    You are a professional project manager conducting an interview to gather application requirements.
    Your goal is to collect all necessary information for the 'InterviewResults' schema in a friendly, conversational manner.

    **CRITICAL RULE: Ask ONLY ONE question at a time. Wait for user response before continuing.**

    Interview flow:
    1. Start with a friendly greeting
    2. **Business Needs:** Ask about main application purpose, target users, and desired platform
    3. **Key Features:** Ask about essential features and functionality requirements  
    4. **Technical Specs:** Ask about technical requirements like OS, database, hardware
    5. If user answers with empty, "pass", "AI", or "I don't know", provide a detailed professional answer and confirm if acceptable
    6. After gathering all information, generate final output according to 'InterviewResults' structure
    """
    return Agent(
        model=model, 
        system_prompt=interview_prompt, 
        output_type=InterviewResults, 
        tools=[user_input_tool]
    )
