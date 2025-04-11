"""
ReAct pattern implementation using OpenRouter models with MCP server integration.
This agent follows the Reasoning, Action, Observation pattern to solve tasks.
"""
import os
import re
import json
import httpx
import asyncio
from typing import Dict, List, Callable, Any, Optional, Tuple
from dotenv import load_dotenv
from client_manager import ClientManager

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
        model: str ="openai/gpt-4o",
        endurance: int = 5,
        config_path: str = None
    ):
        """
        Initialize the ReAct agent.
        
        Args:
            model: OpenRouter model identifier to use
            endurance: Indicate the maximum number of reasoning turns before giving up
            config_path: Path to MCP configuration file
        """
        # Initialize the client manager
        self.client_manager = ClientManager(config_path)
        
        # Set up the agent parameters
        self.model = model
        self.max_turns = endurance**2
        self.action_re = re.compile(r'Action: \[([\w_]+)\|([\w_]+)(?:\|(.*))?\]')
        
        # These will be populated during initialization
        self.actions = {}
        self.system_prompt = ""
        self.initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the ReAct agent asynchronously.
        This needs to be called before using the agent.
        """
        if self.initialized:
            return
            
        # Load configurations, create clients, and connect to servers
        await self.client_manager.start()
        
        # Get tools from all connected clients using the client_manager
        self.actions = self.client_manager.get_tools()
        
        # Create the system prompt with available actions
        action_descriptions = "\r\n".join([
            f"{name}:\r\n\r\n{desc}" 
            for name, (_, desc) in self.actions.items()
        ])
        
        self.system_prompt = f"""
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer.
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then you will get an Observation from that action.
For tool calling return Action [server_name|tool_name|arg1_name:arg1_value,arg2_name:arg2_value]

Example: [filesystem|list_directory|path:C:/Code]

When you have an answer to the question, start your message with "Final answer: " to provide it.

Here are the actions available to you:

{action_descriptions}

Example session:

Question: What is the capital of France?
Thought: I should look up information about France.
Action: [search_server | search_web | key:France capital, year:2025]
PAUSE

Observation: France is a country in Western Europe. The capital of France is Paris.

Thought: I found that the capital of France is Paris.
Final answer: The capital of France is Paris.
"""
        
        self.initialized = True
    
    async def run(self, question: str) -> str:
        """
        Run the ReAct agent on a question.
        
        Args:
            question: The question to answer
            
        Returns:
            Final answer after the reasoning process
        """
        # Make sure the agent is initialized
        if not self.initialized:
            await self.initialize()
            
        turn = 0
        next_prompt = question
        
        # Create the LLM agent for this run
        llm_agent = OpenRouterAgent(system_prompt=self.system_prompt, model=self.model)
        
        while turn < self.max_turns:
            print(f"\n--- Turn {turn + 1} ---")
            response = llm_agent(next_prompt)
            print(f"Response:\r\n{response}")
            
            # Check if we have a final answer
            if "Final answer:" in response:
                # Extract the final answer
                final_answer_match = re.search(r'Final answer:(.*?)(?:$|\n\n)', response, re.DOTALL)
                if final_answer_match:
                    return final_answer_match.group(1).strip()
                else:
                    return response.split("Final answer:")[1].strip()
            
            # Check if we have an action to perform
            action_match = self.action_re.search(response)
            if action_match:
                server_name = action_match.group(1)
                action_name = action_match.group(2)
                action_args = action_match.group(3)
                print(f"Action found in response==>Server name: {server_name}, Action name: {action_name}, action_args: {action_args}")
                
                args = {}
                if action_args:
                    if "," in action_args:
                        for arg in action_args.split(", "):
                            key, value = arg.split(":")
                            args[key] = value
                    else:
                        key = action_args.split(":")[0]
                        value = ":".join(action_args.split(":")[1:])
                        args[key] = value

                # Call the action
                result = await self.client_manager.call_tool(server_name, action_name, args)
                print(f"\nObservation: {result}")
                next_prompt = f"{next_prompt}\r\nObservation: {result}"
            
            turn += 1
        
        return "Reached maximum number of turns without a final answer."
    
    async def cleanup(self) -> None:
        """
        Clean up resources when the agent is done.
        This is an async method and should be awaited.
        """
        try:
            await self.client_manager.close_all_clients()
            print("Closed all MCP client connections")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")


async def run_agent_example() -> None:
    """
    Example of running the ReAct agent.
    """
    print("Testing ReActAgent with MCP tools")
    
    # Get the current directory for the config path
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "mcp_config.json")
    
    agent = None
    try:
        # Create the agent with the config path
        agent = ReActAgent(config_path=config_path, endurance=3)
        
        # Initialize the agent
        await agent.initialize()
        
        # Test the agent with a directory listing question
        print("\nTesting agent with question:")
        question = "What files are in the C:/Code directory?"
        print(f"Question: {question}")
        
        # Run the agent
        answer = await agent.run(question)
        print("\nFinal answer:", answer)
        
    except Exception as e:
        print(f"\nError running agent: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Make sure to clean up resources
        if agent is not None:
            await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(run_agent_example())
