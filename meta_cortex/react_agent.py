"""
ReAct pattern implementation using OpenRouter models with MCP server integration.
This agent follows the Reasoning, Action, Observation pattern to solve tasks.
"""
import os
import re
import json
import httpx
from typing import Dict, List, Callable, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OpenRouterAgent:
    """ReAct agent using OpenRouter API to access various LLM models."""
    
    def __init__(self, system_prompt: str = "", model: str = "anthropic/claude-3-opus:beta"):
        """
        Initialize the OpenRouter agent.
        
        Args:
            system_prompt: Initial system prompt to guide the agent's behavior
            model: OpenRouter model identifier to use
        """
        self.system_prompt = system_prompt
        self.model = model
        self.messages: List[Dict[str, str]] = []
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
            
        if self.system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
    
    def __call__(self, message: str) -> str:
        """
        Process a user message and return the agent's response.
        
        Args:
            message: User message to process
            
        Returns:
            Agent's response
        """
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result
    
    def execute(self) -> str:
        """
        Execute the API call to OpenRouter.
        
        Returns:
            Model's response content
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": self.messages
        }
        
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
            
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]


class ReActAgent:
    """
    ReAct agent that follows the Reasoning, Action, Observation pattern.
    Uses an LLM to decide on actions and processes their results.
    """
    
    def __init__(
        self, 
        actions: Dict[str, Tuple[Callable, str]], 
        model: str = "anthropic/claude-3-opus:beta",
        max_turns: int = 5,
        config_path: str = "mcp_config.json"
    ):
        """
        Initialize the ReAct agent.
        
        Args:
            actions: Dictionary mapping action names to (function, description) tuples
            model: OpenRouter model identifier to use
            max_turns: Maximum number of reasoning turns before giving up
            config_path: Path to the MCP configuration file
        """
        self.actions = actions
        self.max_turns = max_turns
        self.action_re = re.compile(r'^Action: (\w+): (.*)$')
        self.config_path = config_path
        
        # Create the system prompt with available actions
        action_descriptions = "\n".join([
            f"{name}:\ne.g. {name}: {desc}" 
            for name, (_, desc) in actions.items()
        ])
        
        system_prompt = f"""
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer.
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

{action_descriptions}

Example session:

Question: What is the capital of France?
Thought: I should look up information about France.
Action: search: France capital
PAUSE

You will be called again with this:

Observation: France is a country in Western Europe. The capital of France is Paris.

You then output:

Thought: I found that the capital of France is Paris.
Answer: The capital of France is Paris.
""".strip()
        
        self.agent = OpenRouterAgent(system_prompt, model)
    
    def run(self, question: str) -> str:
        """
        Run the ReAct agent on a question.
        
        Args:
            question: The question to answer
            
        Returns:
            Final answer after the reasoning process
        """
        turn = 0
        next_prompt = question
        
        while turn < self.max_turns:
            turn += 1
            result = self.agent(next_prompt)
            print(f"\n--- Turn {turn} ---")
            print(result)
            
            # Check if there's an action to run
            actions = [self.action_re.match(a) for a in result.split('\n') if self.action_re.match(a)]
            
            if not actions:
                # No more actions, return the final result
                return result
                
            # Execute the action
            action_match = actions[0]
            action_name, action_input = action_match.groups()
            
            if action_name not in self.actions:
                return f"Error: Unknown action: {action_name}"
                
            action_func, _ = self.actions[action_name]
            print(f"Running: {action_name}({action_input})")
            
            try:
                observation = action_func(action_input)
                print(f"Observation: {observation}")
                next_prompt = f"Observation: {observation}"
            except Exception as e:
                next_prompt = f"Observation: Error executing {action_name}: {str(e)}"
                print(next_prompt)
        
        return "Reached maximum number of turns without a final answer."


# Example usage
if __name__ == "__main__":
    from mcp_tools import MCPTools
    
    # Create MCP tools
    mcp_tools = MCPTools("mcp_config.json")
    
    # Get all available MCP tools
    actions = mcp_tools.get_available_tools()
    
    # Create the agent with MCP actions
    agent = ReActAgent(actions)
    
    try:
        # Test the agent
        question = "What files are in the C:/Code directory?"
        print(f"\nQuestion: {question}")
        answer = agent.run(question)
        print("\nFinal answer:", answer)
    finally:
        # Clean up resources
        mcp_tools.cleanup()
