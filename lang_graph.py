"""
LangGraph Agentic Workflow Orchestrator for SSDLC
Acts as a chat-based orchestrator that uses intelligent agents to understand user intent 
and automatically triggers workflow stages based on agent analysis.
"""
import json
import re
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from dataclasses import dataclass

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Import agents
from agents.interview_agent import create_interview_agent
from agents.environment_agent import create_environment_agent
from agents.security_agent import create_security_requirement_agent
from agents.design_agent import create_design_agent
from agents.documentation_agent import create_generator_agent

# Import shared utilities
from agents.utils import (
    setup_model, Memory, create_memory_tools,
    save_document_file, safe_run_agent, retry_with_delay_and_confirmation,
    console
)

# Import for intent understanding agent
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Intent Understanding Models
class IntentAnalysis(BaseModel):
    """Model for intent analysis results"""
    intent_type: str = Field(description="Type of intent: 'app_development', 'general_chat', 'help', 'status'")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    app_type: Optional[str] = Field(default=None, description="Type of application if app_development intent")
    workflow_action: str = Field(description="Action to take: 'start_workflow', 'continue_workflow', 'chat_mode', 'end'")
    reasoning: str = Field(description="Explanation of the intent analysis")

class IntentUnderstandingAgent:
    """Agent that understands user intent and determines workflow direction"""
    
    def __init__(self, model):
        self.model = model
        
        # Create pydantic_ai Agent for intent analysis
        intent_prompt = """
You are an intelligent intent understanding agent for a Secure Software Development Life Cycle (SSDLC) system.

Your job is to analyze user input and determine their intent, then provide structured output.

Intent Types:
- 'app_development': User wants to create/build/develop an application
- 'general_chat': Regular conversation
- 'help': User needs assistance or information  
- 'status': User wants to know current progress

Workflow Actions:
- 'start_workflow': Begin new app development workflow
- 'continue_workflow': Continue existing workflow
- 'chat_mode': Handle as general conversation
- 'end': End current workflow

Keywords for app development:
- make/create/build/develop + app/application
- specific app types: cashier, POS, inventory, management, etc.
- "new app", "app development"

Analyze the user input carefully and provide structured output with:
- intent_type: one of the types above
- confidence: 0.0 to 1.0
- app_type: type of app if relevant (can be null)
- workflow_action: one of the actions above
- reasoning: explanation of your analysis

Be precise and confident in your analysis.
"""
        
        self.agent = Agent(
            model=model,
            system_prompt=intent_prompt,
            output_type=IntentAnalysis
        )
    
    def analyze_intent(self, user_input: str, workflow_status: dict) -> IntentAnalysis:
        """Analyze user intent and return structured decision"""
        try:
            # Create context for the agent
            context = f"""
User input: "{user_input}"

Current workflow status:
- Workflow active: {workflow_status.get('workflow_active', False)}
- Current stage: {workflow_status.get('current_stage', 'none')}
- Completed stages: {list(workflow_status.get('stage_completed', {}).keys())}

Analyze this input and determine the user's intent.
"""
            
            # Use pydantic_ai Agent to analyze intent
            result = self.agent.run_sync(context)
            return result.output  # Use .output instead of .data
            
        except Exception as e:
            console.print(f"[bold red]Intent analysis error:[/bold red] {e}")
            # Fallback to simple keyword matching
            return self._fallback_intent_analysis(user_input, workflow_status)
    
    def _fallback_intent_analysis(self, user_input: str, workflow_status: dict) -> IntentAnalysis:
        """Fallback intent analysis using simple keyword matching"""
        user_input_lower = user_input.lower().strip()
        
        # App development keywords
        app_keywords = [
            "make app", "create app", "build app", "develop app",
            "make application", "create application", "build application",
            "new app", "new application", "app development",
            "cashier app", "pos app", "inventory app", "management app"
        ]
        
        # Help keywords
        help_keywords = ["help", "what can you do", "commands", "how to"]
        
        # Status keywords
        status_keywords = ["status", "progress", "where are we", "current stage"]
        
        if any(keyword in user_input_lower for keyword in app_keywords):
            if not workflow_status.get("workflow_active", False):
                return IntentAnalysis(
                    intent_type="app_development",
                    confidence=0.9,
                    app_type="general",
                    workflow_action="start_workflow",
                    reasoning="User requested app development and no workflow is active"
                )
            else:
                return IntentAnalysis(
                    intent_type="app_development",
                    confidence=0.8,
                    app_type=None,
                    workflow_action="continue_workflow",
                    reasoning="User mentioned app development and workflow is already active"
                )
        elif any(keyword in user_input_lower for keyword in help_keywords):
            return IntentAnalysis(
                intent_type="help",
                confidence=0.9,
                app_type=None,
                workflow_action="chat_mode",
                reasoning="User is asking for help"
            )
        elif any(keyword in user_input_lower for keyword in status_keywords):
            return IntentAnalysis(
                intent_type="status",
                confidence=0.9,
                app_type=None,
                workflow_action="chat_mode",
                reasoning="User is asking for status information"
            )
        else:
            return IntentAnalysis(
                intent_type="general_chat",
                confidence=0.7,
                app_type=None,
                workflow_action="chat_mode",
                reasoning="General conversation detected"
            )

# State for the graph
class WorkflowState(TypedDict):
    messages: Annotated[List, "List of conversation messages"]
    current_stage: str
    workflow_active: bool
    user_input: str
    shared_memory: Dict[str, Any]
    stage_completed: Dict[str, bool]
    last_agent_response: Optional[str]
    intent_analysis: Optional[Dict[str, Any]]

@dataclass
class OrchestrationConfig:
    """Configuration for the orchestrator"""
    model: Any
    memory: Memory
    memory_tools: List
    console: Console
    intent_agent: IntentUnderstandingAgent

class SSLDCOrchestrator:
    """
    LangGraph-based orchestrator for SSDLC workflow.
    Uses intelligent intent understanding agents to manage conversation flow 
    and automatically trigger appropriate workflow stages based on advanced NLP analysis.
    """
    
    def __init__(self):
        self.config = self._setup_config()
        self.workflow = self._create_workflow()
        
    def _setup_config(self) -> OrchestrationConfig:
        """Setup the orchestrator configuration"""
        model = setup_model()
        shared_memory = Memory()
        memory_tools = create_memory_tools(shared_memory)
        intent_agent = IntentUnderstandingAgent(model)
        
        return OrchestrationConfig(
            model=model,
            memory=shared_memory,
            memory_tools=memory_tools,
            console=console,
            intent_agent=intent_agent
        )
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("intent_agent", self._intent_analysis)
        workflow.add_node("chat_mode", self._chat_mode)
        workflow.add_node("interview_stage", self._interview_stage)
        workflow.add_node("environment_stage", self._environment_stage)
        workflow.add_node("security_stage", self._security_stage)
        workflow.add_node("design_stage", self._design_stage)
        workflow.add_node("generation_stage", self._generation_stage)
        workflow.add_node("workflow_complete", self._workflow_complete)
        
        # Define edges
        workflow.add_edge(START, "intent_agent")
        
        # Intent agent decides next step
        workflow.add_conditional_edges(
            "intent_agent",
            self._complete_intent_routing,
            {
                "chat_mode": "chat_mode",
                "interview_stage": "interview_stage",
                "environment_stage": "environment_stage",
                "security_stage": "security_stage", 
                "design_stage": "design_stage",
                "generation_stage": "generation_stage",
                "end": END
            }
        )
        
        # Workflow progression
        workflow.add_edge("interview_stage", "environment_stage")
        workflow.add_edge("environment_stage", "security_stage")
        workflow.add_edge("security_stage", "design_stage")
        workflow.add_edge("design_stage", "generation_stage")
        workflow.add_edge("generation_stage", "workflow_complete")
        
        # Chat mode ends the conversation turn, workflow_complete returns to intent agent for new input
        workflow.add_edge("chat_mode", END)
        workflow.add_edge("workflow_complete", END)
        
        # Setup memory
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        
        return app
    
    def _intent_analysis(self, state: WorkflowState) -> WorkflowState:
        """Intent analysis node - uses agent to understand user intent"""
        user_input = state.get("user_input", "").strip()
        
        if not user_input:
            return state
        
        # Check if workflow files already exist
        existing_files = self._check_existing_workflow_files()
        
        # Prepare workflow status for intent agent
        workflow_status = {
            "workflow_active": state.get("workflow_active", False),
            "current_stage": state.get("current_stage", ""),
            "stage_completed": state.get("stage_completed", {}),
            "existing_files": existing_files
        }
        
        # Use intent agent to analyze user input
        console.print("[bold blue]🧠 Analyzing intent...[/bold blue]")
        
        try:
            intent_result = self.config.intent_agent.analyze_intent(user_input, workflow_status)
            
            console.print(f"[bold green]Intent:[/bold green] {intent_result.intent_type} "
                         f"[bold yellow]({intent_result.confidence:.2f})[/bold yellow]")
            console.print(f"[bold cyan]Reasoning:[/bold cyan] {intent_result.reasoning}")
            
            # Update state based on intent analysis
            state["intent_analysis"] = intent_result.model_dump()
            
            # Handle workflow activation with existing files detection
            if intent_result.workflow_action == "start_workflow":
                if not state.get("workflow_active", False):
                    state["workflow_active"] = True
                    
                    # Determine starting stage based on existing files
                    if all(existing_files.values()):  # All files exist
                        console.print("[bold green]📄 All workflow files found! Proceeding to code generation[/bold green]")
                        self._load_all_existing_data()
                        state["current_stage"] = "generation"
                        state["stage_completed"] = {
                            "interview": True,
                            "environment": True,
                            "security": True,
                            "design": True,
                            "generation": False
                        }
                        console.print(Panel(
                            f"🚀 Resuming App Development Workflow\n\n"
                            f"Intent: {intent_result.intent_type}\n"
                            f"App Type: {intent_result.app_type or 'General'}\n"
                            f"Confidence: {intent_result.confidence:.2%}\n\n"
                            f"📄 All stages completed - proceeding directly to Code Generation!",
                            title="[bold magenta]Workflow Resumed by Agent[/bold magenta]",
                            subtitle="[cyan]Jumping to Code Generation[/cyan]"
                        ))
                    elif existing_files["interview"]:
                        console.print("[bold green]📄 Found existing interview results![/bold green]")
                        # Load existing interview data into memory
                        self._load_existing_interview_data()
                        
                        # Determine next stage based on what's missing
                        if not existing_files["environment"]:
                            state["current_stage"] = "environment"
                        elif not existing_files["security"]:
                            state["current_stage"] = "security"
                        elif not existing_files["design"]:
                            state["current_stage"] = "design"
                        else:
                            state["current_stage"] = "generation"
                            
                        state["stage_completed"] = {
                            "interview": True,
                            "environment": existing_files["environment"],
                            "security": existing_files["security"],
                            "design": existing_files["design"],
                            "generation": False
                        }
                        console.print(Panel(
                            f"🚀 Resuming App Development Workflow\n\n"
                            f"Intent: {intent_result.intent_type}\n"
                            f"App Type: {intent_result.app_type or 'General'}\n"
                            f"Confidence: {intent_result.confidence:.2%}\n\n"
                            f"📄 Interview completed - proceeding to {state['current_stage'].title()} stage",
                            title="[bold magenta]Workflow Resumed by Agent[/bold magenta]",
                            subtitle=f"[cyan]Skipping to {state['current_stage'].title()} Stage[/cyan]"
                        ))
                    else:
                        state["current_stage"] = "interview"
                        state["stage_completed"] = {
                            "interview": False,
                            "environment": False,
                            "security": False,
                            "design": False,
                            "generation": False
                        }
                        console.print(Panel(
                            f"🚀 Starting App Development Workflow\n\n"
                            f"Intent: {intent_result.intent_type}\n"
                            f"App Type: {intent_result.app_type or 'General'}\n"
                            f"Confidence: {intent_result.confidence:.2%}",
                            title="[bold magenta]Workflow Initiated by Agent[/bold magenta]",
                            subtitle="[cyan]Beginning with requirements interview[/cyan]"
                        ))
            
        except Exception as e:
            console.print(f"[bold red]❌ Intent analysis error:[/bold red] {e}")
            # Fallback to chat mode
            state["intent_analysis"] = {
                "intent_type": "general_chat",
                "workflow_action": "chat_mode",
                "confidence": 0.5,
                "reasoning": "Error in intent analysis, defaulting to chat mode"
            }
        
        return state
    
    def _check_existing_workflow_files(self) -> Dict[str, bool]:
        """Check which workflow files already exist"""
        import os
        
        files_to_check = {
            "interview": "Interview_Results.json",
            "environment": "Environment_Requirements.json", 
            "security": "Security_Requirements.json",
            "design": "System_Design.json"
        }
        
        existing_files = {}
        for stage, filename in files_to_check.items():
            existing_files[stage] = os.path.exists(filename)
            if existing_files[stage]:
                console.print(f"[bold blue]📄 Found existing:[/bold blue] {filename}")
        
        return existing_files
    
    def _load_existing_interview_data(self):
        """Load existing interview data into memory"""
        try:
            import json
            with open("Interview_Results.json", "r", encoding="utf-8") as f:
                interview_data = f.read()
            
            # Load into shared memory
            self.config.memory.set("interview_results", interview_data)
            console.print("[bold green]✅ Loaded existing interview data into memory[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]❌ Error loading interview data:[/bold red] {e}")
    
    def _intent_condition(self, state: WorkflowState) -> str:
        """Conditional logic based on intent analysis"""
        intent_analysis = state.get("intent_analysis", {})
        workflow_action = intent_analysis.get("workflow_action", "chat_mode")
        
        # Check if workflow is active and stages
        if state.get("workflow_active", False):
            current_stage = state.get("current_stage", "")
            stage_completed = state.get("stage_completed", {})
            
            # If in middle of workflow, continue appropriately
            if current_stage == "interview" and not stage_completed.get("interview", False):
                return "start_workflow"
            elif current_stage == "environment" and not stage_completed.get("environment", False):
                return "continue_workflow"  # This will go to environment_stage
            elif current_stage in ["security", "design", "generation"]:
                return "continue_workflow"
            elif all(stage_completed.values()):
                return "end"
        
        # Otherwise follow intent agent decision
        if workflow_action == "start_workflow":
            return "start_workflow"
        elif workflow_action == "continue_workflow":
            return "continue_workflow"
        elif workflow_action == "end":
            return "end"
        else:
            return "chat_mode"
    
    def _complete_intent_routing(self, state: WorkflowState) -> str:
        """Complete routing logic that determines exact next stage"""
        intent_analysis = state.get("intent_analysis", {})
        workflow_action = intent_analysis.get("workflow_action", "chat_mode")
        
        # If not app development intent, go to chat mode
        if workflow_action == "chat_mode":
            return "chat_mode"
        elif workflow_action == "end":
            return "end"
        
        # For app development intents, determine the right stage
        if state.get("workflow_active", False):
            current_stage = state.get("current_stage", "")
            stage_completed = state.get("stage_completed", {})
            
            # Route to current stage if not completed
            if current_stage == "interview" and not stage_completed.get("interview", False):
                return "interview_stage"
            elif current_stage == "environment" and not stage_completed.get("environment", False):
                return "environment_stage"
            elif current_stage == "security" and not stage_completed.get("security", False):
                return "security_stage"
            elif current_stage == "design" and not stage_completed.get("design", False):
                return "design_stage"
            elif current_stage == "generation" and not stage_completed.get("generation", False):
                return "generation_stage"
            elif all(stage_completed.values()):
                return "end"
        
        # Default case - start from interview
        return "interview_stage"
    
    def _chat_mode(self, state: WorkflowState) -> WorkflowState:
        """Regular chat mode - general conversation"""
        user_input = state.get("user_input", "")
        
        # Simple AI response for general chat
        response = self._generate_chat_response(user_input, state)
        
        # Add to message history
        state["messages"].append(HumanMessage(content=user_input))
        state["messages"].append(AIMessage(content=response))
        state["last_agent_response"] = response
        
        console.print(f"[bold cyan]Assistant:[/bold cyan] {response}")
        
        return state
    
    def _interview_stage(self, state: WorkflowState) -> WorkflowState:
        """Interview stage - collect requirements"""
        console.print("\n[bold]🎤 Starting Interview Stage[/bold]")
        
        interview_agent = create_interview_agent(self.config.model)
        user_input = state.get("user_input", "")
        
        try:
            interview_result = retry_with_delay_and_confirmation(
                safe_run_agent,
                interview_agent,
                user_input,
                "Interview Stage"
            )
            
            if interview_result is not None:
                interview_structured = json.dumps(
                    interview_result.output.model_dump(), 
                    indent=2, 
                    default=str, 
                    ensure_ascii=False
                )
                
                self.config.memory.set("interview_results", interview_structured)
                state["shared_memory"]["interview_results"] = interview_structured
                state["stage_completed"]["interview"] = True
                state["current_stage"] = "environment"
                
                console.print("\n[bold green]✅ Interview completed![/bold green]")
                save_document_file("Interview_Results.json", interview_structured)
                
                response = "Great! I've gathered your requirements. Now let me create the environment requirements for your application."
                state["last_agent_response"] = response
                
            else:
                console.print("\n[bold yellow]⚠️ Interview stage failed, but continuing...[/bold yellow]")
                state["stage_completed"]["interview"] = True
                state["current_stage"] = "environment"
                state["last_agent_response"] = "I'll continue with default requirements."
                
        except Exception as e:
            console.print(f"[bold red]❌ Interview stage error:[/bold red] {e}")
            state["stage_completed"]["interview"] = True
            state["current_stage"] = "environment"
        
        return state
    
    def _environment_stage(self, state: WorkflowState) -> WorkflowState:
        """Environment requirements stage"""
        console.print("\n[bold]🌍 Creating Environment Requirements[/bold]")
        
        environment_agent = create_environment_agent(self.config.model, self.config.memory_tools)
        
        try:
            environment_doc = retry_with_delay_and_confirmation(
                safe_run_agent,
                environment_agent,
                "Create EnvironmentRequirements document based on interview results.",
                "Environment Requirements Stage"
            )
            
            if environment_doc is not None:
                environment_structured = json.dumps(
                    environment_doc.output.model_dump(),
                    indent=2,
                    default=str,
                    ensure_ascii=False
                )
                
                self.config.memory.set("environment_requirements", environment_structured)
                state["shared_memory"]["environment_requirements"] = environment_structured
                save_document_file("Environment_Requirements.json", environment_structured)
                console.print("\n[bold green]✅ Environment requirements created![/bold green]")
                
            state["stage_completed"]["environment"] = True
            state["current_stage"] = "security"
            
        except Exception as e:
            console.print(f"[bold red]❌ Environment stage error:[/bold red] {e}")
            state["stage_completed"]["environment"] = True
            state["current_stage"] = "security"
        
        return state
    
    def _security_stage(self, state: WorkflowState) -> WorkflowState:
        """Security requirements stage"""
        console.print("\n[bold]🔒 Creating Security Requirements[/bold]")
        
        security_agent = create_security_requirement_agent(self.config.model, self.config.memory_tools)
        
        try:
            security_doc = retry_with_delay_and_confirmation(
                safe_run_agent,
                security_agent,
                "Create SecurityRequirements document for this application.",
                "Security Requirements Stage"
            )
            
            if security_doc is not None:
                security_structured = json.dumps(
                    security_doc.output.model_dump(),
                    indent=2,
                    default=str,
                    ensure_ascii=False
                )
                
                self.config.memory.set("security_requirements", security_structured)
                state["shared_memory"]["security_requirements"] = security_structured
                save_document_file("Security_Requirements.json", security_structured)
                console.print("\n[bold green]✅ Security requirements created![/bold green]")
                
            state["stage_completed"]["security"] = True
            state["current_stage"] = "design"
            
        except Exception as e:
            console.print(f"[bold red]❌ Security stage error:[/bold red] {e}")
            state["stage_completed"]["security"] = True
            state["current_stage"] = "design"
        
        return state
    
    def _design_stage(self, state: WorkflowState) -> WorkflowState:
        """Design stage"""
        console.print("\n[bold]🎨 Creating System Design[/bold]")
        
        design_agent = create_design_agent(self.config.model, self.config.memory_tools)
        
        try:
            design_doc = retry_with_delay_and_confirmation(
                safe_run_agent,
                design_agent,
                "Create SystemDesign document based on all existing documents.",
                "System Design Stage"
            )
            
            if design_doc is not None:
                design_structured = json.dumps(
                    design_doc.output.model_dump(),
                    indent=2,
                    default=str,
                    ensure_ascii=False
                )
                
                self.config.memory.set("system_design", design_structured)
                state["shared_memory"]["system_design"] = design_structured
                save_document_file("System_Design.json", design_structured)
                console.print("\n[bold green]✅ System design created![/bold green]")
                
            state["stage_completed"]["design"] = True
            state["current_stage"] = "generation"
            
        except Exception as e:
            console.print(f"[bold red]❌ Design stage error:[/bold red] {e}")
            state["stage_completed"]["design"] = True
            state["current_stage"] = "generation"
        
        return state
    
    def _generation_stage(self, state: WorkflowState) -> WorkflowState:
        """Code and documentation generation stage"""
        console.print("\n[bold]⚡ Generating Code and Documentation[/bold]")
        
        generator_agent = create_generator_agent(self.config.model, self.config.memory_tools)
        
        try:
            # Generate documentation and code
            generation_result = retry_with_delay_and_confirmation(
                safe_run_agent,
                generator_agent,
                "Generate comprehensive documentation with Mermaid diagrams and functional application code based on all available documents",
                "Generation Stage"
            )
            
            console.print("\n[bold green]✅ Code and documentation generated![/bold green]")
            state["stage_completed"]["generation"] = True
            
        except Exception as e:
            console.print(f"[bold red]❌ Generation stage error:[/bold red] {e}")
            state["stage_completed"]["generation"] = True
        
        return state
    
    def _workflow_complete(self, state: WorkflowState) -> WorkflowState:
        """Workflow completion"""
        console.print(Panel(
            "🎉 App Development Workflow Complete!\n\nAll documents and code have been generated. You can now continue with normal chat.",
            title="[bold magenta]Workflow Completed[/bold magenta]",
            style="green"
        ))
        
        state["workflow_active"] = False
        state["current_stage"] = "complete"
        state["last_agent_response"] = "Your application development workflow is complete! All documents and code have been generated. How can I help you further?"
        
        return state
    
    def _generate_chat_response(self, user_input: str, state: WorkflowState) -> str:
        """Generate response for general chat mode using intent analysis"""
        intent_analysis = state.get("intent_analysis", {})
        intent_type = intent_analysis.get("intent_type", "general_chat")
        
        # Use intent information to provide better responses
        if intent_type == "help":
            return ("I'm your SSDLC assistant! I can help you with:\n"
                   "• App development workflow (just say 'make app' or 'create application')\n"
                   "• General questions about software development\n"
                   "• Security requirements and best practices\n"
                   "• System design guidance\n\n"
                   "To start building an app, just tell me what kind of application you want to create!")
        
        elif intent_type == "status":
            if state.get("workflow_active", False):
                current_stage = state.get("current_stage", "unknown")
                completed = state.get("stage_completed", {})
                completed_stages = [k for k, v in completed.items() if v]
                confidence = intent_analysis.get("confidence", 0)
                
                status_text = f"Workflow is active. Current stage: {current_stage}.\n"
                status_text += f"Completed stages: {', '.join(completed_stages) if completed_stages else 'none'}\n"
                status_text += f"Intent confidence: {confidence:.2%}"
                return status_text
            else:
                return "No active workflow. Start by telling me what kind of app you want to create!"
        
        elif intent_type == "app_development":
            app_type = intent_analysis.get("app_type", "application")
            confidence = intent_analysis.get("confidence", 0)
            return (f"I understand you want to develop a {app_type} (confidence: {confidence:.2%}). "
                   f"Let me help you start the development workflow!")
        
        # Greeting responses (fallback check)
        user_input_lower = user_input.lower()
        if any(word in user_input_lower for word in ["hi", "hello", "hey", "good morning", "good afternoon"]):
            return "Hello! I'm here to help you with secure software development. What would you like to work on today?"
        
        # Default response with intent information
        reasoning = intent_analysis.get("reasoning", "No specific intent detected")
        return (f"I understand you want to discuss that. {reasoning}\n\n"
               f"If you'd like to create an application, just let me know what kind of app you want to build "
               f"and I'll guide you through the process!")
    
    def run_chat(self):
        """Run the interactive chat interface"""
        console.print(Panel(
            "🤖 SSDLC Agentic Orchestrator with AI Intent Understanding\n\n"
            "I use advanced AI agents to understand your intent and guide you!\n"
            "• To create an app: describe what you want to build in natural language\n"
            "• For general chat: ask me anything about software development\n"
            "• For help: ask 'what can you do?' or 'help'\n"
            "• Type 'exit' to quit\n\n"
            "💡 I'll intelligently analyze your messages to provide the best assistance!",
            title="[bold magenta]Welcome to AI-Powered SSDLC[/bold magenta]",
            style="cyan"
        ))
        
        # Initialize state
        config = {"configurable": {"thread_id": "ssdlc_chat"}}
        initial_state = {
            "messages": [],
            "current_stage": "",
            "workflow_active": False,
            "user_input": "",
            "shared_memory": {},
            "stage_completed": {},
            "last_agent_response": None,
            "intent_analysis": None
        }
        
        while True:
            try:
                # Get user input
                user_input = input("\n🧑 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    console.print("[bold yellow]👋 Goodbye![/bold yellow]")
                    break
                
                # Update state with user input
                current_state = initial_state.copy()
                current_state["user_input"] = user_input
                
                # Run workflow
                result = self.workflow.invoke(current_state, config)
                
                # Update initial state for next iteration
                initial_state = result
                
                # Show assistant response if available
                if result.get("last_agent_response"):
                    console.print(f"[bold cyan]🤖 Assistant:[/bold cyan] {result['last_agent_response']}")
                
            except KeyboardInterrupt:
                console.print("\n[bold yellow]👋 Chat interrupted. Goodbye![/bold yellow]")
                break
            except Exception as e:
                console.print(f"[bold red]❌ Error:[/bold red] {e}")
                continue

def main():
    """Main function to start the orchestrator"""
    try:
        orchestrator = SSLDCOrchestrator()
        orchestrator.run_chat()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Goodbye![/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to start orchestrator:[/bold red] {e}")

if __name__ == "__main__":
    main()
