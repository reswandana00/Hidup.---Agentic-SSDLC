"""
Generator Agent for creating Mermaid diagrams and code files.
Can generate both documentation diagrams and application code.
"""
import os
import re
from pydantic_ai import Agent, RunContext
from .models import FileAction
from .utils import user_input_tool


class FileManager:
    """Unified file manager for both Mermaid and code files."""
    
    def execute(self, action: FileAction):
        if action.action == "create":
            return self._create(action.file_path, action.content)
        elif action.action == "read":
            return self._read(action.file_path)
        elif action.action == "edit":
            return self._edit(action.file_path, action.pattern, action.content)
        elif action.action == "delete":
            return self._delete(action.file_path)
        else:
            raise ValueError(f"Unsupported action: {action.action}")

    def _create(self, path: str, content: str):
        if not content:
            raise ValueError("Content cannot be empty for file creation")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        
        return f"File {path} created successfully."

    def _read(self, path: str):
        if not os.path.exists(path):
            return f"File {path} not found."
        
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _edit(self, path: str, pattern: str, replacement: str):
        if not os.path.exists(path):
            return f"File {path} not found for editing."
        
        if not pattern or not replacement:
            raise ValueError("Pattern and replacement must be provided for edit")
        
        text = self._read(path)
        if isinstance(text, str) and "not found" in text:
            return text
        
        new_text = re.sub(pattern, replacement, text, flags=re.MULTILINE | re.DOTALL)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        
        return f"File {path} edited successfully."

    def _delete(self, path: str):
        if not os.path.exists(path):
            return f"File {path} not found for deletion."
        
        os.remove(path)
        return f"File {path} deleted successfully."


def create_generator_agent(model, memory_tools):
    """Create unified generator agent for Mermaid diagrams and code."""
    file_manager = FileManager()
    
    def execute_file_action(ctx: RunContext, action: FileAction) -> str:
        """Execute file actions like create, read, edit, or delete files"""
        try:
            result = file_manager.execute(action)
            return result
        except Exception as e:
            return f"Error executing action: {str(e)}"
    
    generator_prompt = """
    You are an expert generator that can create:
    1. **Mermaid Diagrams**: flowcharts, sequence diagrams, class diagrams, architecture diagrams, etc.
    2. **Application Code**: Python, JavaScript, HTML, CSS, and other programming languages in file
    3. **Documentation**: Markdown files text only

    **For Mermaid Diagrams:**
    - Use proper Mermaid syntax for the diagram type
    - Keep diagrams simple and clear
    - Save as .md files with markdown code blocks or .mermaid for pure diagrams
    - Valid diagram types: flowchart, sequenceDiagram, classDiagram, stateDiagram, erDiagram, architecture, c4Context, etc.

    **For Code Generation:**
    - Write clean, professional code with proper structure
    - Include comments and documentation
    - Follow best practices for the target language
    - Consider security and maintainability

    **File Operations:**
    - action="create": Create new files with content
    - action="read": Read existing files
    - action="edit": Edit files using regex patterns
    - action="delete": Delete files

    **Memory Access:**
    - Use `list_available_documents_tool` to see available documents
    - Use `read_document_tool` to read specific documents for context
    - Use this information to generate appropriate diagrams and code

    Write documentation in folders
    Always provide complete, working solutions based on the available documentation.
    """
    
    return Agent(
        model=model,
        system_prompt=generator_prompt,
        tools=[execute_file_action, user_input_tool] + memory_tools
    )
