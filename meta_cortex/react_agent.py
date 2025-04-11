"""
ReAct pattern implementation using OpenRouter models with MCP server integration.
This agent follows the Reasoning, Action, Observation pattern to solve tasks.
"""
import os
import re
import json
import httpx
import asyncio
import yaml
from typing import Dict, List, Callable, Any, Optional, Tuple
from dotenv import load_dotenv
from client_manager import ClientManager
from agent_config import AgentConfig

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
            "messages": self.messages,
            "max_tokens": 1000  # Limit token usage to avoid credit issues
        }
        
        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0  # Add a timeout to prevent hanging
            )
            
            if response.status_code != 200:
                error_msg = f"API call failed with status code {response.status_code}: {response.text}"
                print(error_msg)
                return f"Error: {error_msg}"
                
            response_data = response.json()
            
            # Check if the response has the expected format
            if "choices" not in response_data or not response_data["choices"]:
                print(f"Unexpected API response format: {response_data}")
                return "Error: Unexpected API response format"
                
            return response_data["choices"][0]["message"]["content"]
            
        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            print(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Error during API call: {str(e)}"
            print(error_msg)
            return f"Error: {error_msg}"


class ReActAgent:
    """
    ReAct agent that follows the Reasoning, Action, Observation pattern.
    Uses an LLM to decide on actions and processes their results.
    """
    
    def __init__(
        self, 
        model: str = None,
        endurance: int = None,
        config_path: str = None,
        agent_config_path: str = None
    ):
        """
        Initialize the ReAct agent.
        
        Args:
            model: OpenRouter model identifier to use (overrides agent config if provided)
            endurance: Indicate the maximum number of reasoning turns before giving up (overrides agent config if provided)
            config_path: Path to MCP configuration file
            agent_config_path: Path to agent configuration YAML file
        """
        # Initialize the client manager
        self.client_manager = ClientManager(config_path)
        
        # Load agent configuration if available
        self.agent_config = AgentConfig(agent_config_path)
        self.agent_data = self.agent_config.get_agent_config("assistant_agent")
        
        # Set up the agent parameters, using config values if available
        self.model = model or self.agent_data.get("model", "openai/gpt-4o").strip()
        
        # Parse endurance from config if not provided directly
        config_endurance = self.agent_data.get("endurance")
        if config_endurance and not endurance:
            try:
                endurance = int(config_endurance.strip())
            except (ValueError, TypeError):
                endurance = 5
        
        self.endurance = endurance or 5
        self.max_turns = self.endurance**2
        self.action_re = re.compile(r'Action: \[(\w+)\|(\w+)(?:\|(.*))?\]')
        
        # Get role, goal, and backstory from agent config
        self.role = self.agent_data.get("role", "").strip()
        self.goal = self.agent_data.get("goal", "").strip()
        self.backstory = self.agent_data.get("backstory", "").strip()
        
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
        
        # Create a description of all available actions for the system prompt
        action_descriptions = "\n".join([
            f"- {name}: {description}" 
            for name, (_, description) in self.actions.items()
        ])
        
        # Load system prompt from file
        try:
            # Get the current directory for the prompt path
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            prompt_path = os.path.join(base_dir, "prompts", "react_agent.txt")
            
            with open(prompt_path, 'r') as f:
                prompt_template = f.read()
            
            # Replace tags with values
            self.system_prompt = prompt_template.replace("{{action_descriptions}}", action_descriptions)
            
            # Add agent's role, goal, and backstory if available
            agent_persona = ""
            if self.role:
                agent_persona += f"\n\nYOUR ROLE:\n{self.role}"
            if self.goal:
                agent_persona += f"\n\nYOUR GOAL:\n{self.goal}"
            if self.backstory:
                agent_persona += f"\n\nYOUR BACKSTORY:\n{self.backstory}"
            
            # Add the agent persona to the system prompt
            if agent_persona:
                self.system_prompt += agent_persona
            
            print(f"Loaded system prompt from {prompt_path} with agent persona")
        except Exception as e:
            print(f"Error loading system prompt: {str(e)}")
            # Fallback to a default prompt if file loading fails
            self.system_prompt = f"""You run in a loop of Thought, Action, PAUSE, Observation.
Use Action to run one of the actions available to you.
For tool calling return Action [server_name|tool_name|arg1_name:arg1_value]
When you have an answer, start with "Final answer: "

Here are the actions available to you:

{action_descriptions}
"""
            
            # Add agent's role, goal, and backstory to fallback prompt if available
            if self.role:
                self.system_prompt += f"\n\nYOUR ROLE:\n{self.role}"
            if self.goal:
                self.system_prompt += f"\n\nYOUR GOAL:\n{self.goal}"
            if self.backstory:
                self.system_prompt += f"\n\nYOUR BACKSTORY:\n{self.backstory}"
        
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
                return response
            
            # Check if we have an action to perform
            action_match = self.action_re.search(response)
            if action_match:
                server_name = action_match.group(1)
                action_name = action_match.group(2)
                action_args = action_match.group(3)
                #print(f"Action found in response==>Server name: {server_name}, Action name: {action_name}, action_args: {action_args}")
                
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
            # Ensure client_manager exists before trying to close clients
            if hasattr(self, 'client_manager') and self.client_manager is not None:
                await self.client_manager.close_all_clients()
                print("Closed all MCP client connections")
            else:
                print("No client manager to clean up")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
        finally:
            # Ensure all resources are properly released
            if hasattr(self, 'client_manager'):
                self.client_manager = None


async def run_agent_example() -> None:
    """
    Example of running the ReAct agent.
    """
    print("Testing ReActAgent with MCP tools")
    
    # Get the current directory for the config paths
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "mcp_config.json")
    
    # Path to the agent configuration file
    project_dir = os.path.dirname(base_dir)
    agent_config_path = os.path.join(project_dir, "prompts", "agents.yaml")
    
    agent = None
    try:
        # Create the agent with both config paths
        agent = ReActAgent(
            config_path=config_path,
            agent_config_path=agent_config_path
        )
        
        # Initialize the agent
        await agent.initialize()
        
        # Test the agent with a directory listing question
        print("\nTesting agent with question:")
        question = "What files are in the C:/Code directory?"
        print(f"Question: {question}")
        
        # Run the agent
        answer = await agent.run(question)
        #print("\nFinal answer:", answer)

        question2 = "What are the lates news in cnn.com?"
        answer2 = await agent.run(question2)
        #print("\nFinal answer:", answer2)
        
    except Exception as e:
        print(f"\nError running agent: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Make sure to clean up resources
        if agent is not None:
            try:
                await agent.cleanup()
                print("Cleanup completed successfully")
            except Exception as e:
                print(f"Error during final cleanup: {str(e)}")

if __name__ == "__main__":
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the main function
        loop.run_until_complete(run_agent_example())
    finally:
        # Give pending tasks a chance to complete
        pending = asyncio.all_tasks(loop)
        for task in pending:
            if not task.done():
                task.cancel()
        
        # Allow the loop to process the cancellations
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
        # A simpler approach to avoid subprocess cleanup issues
        # First, run a small event loop to allow any pending operations to complete
        try:
            # Create a dummy task that just sleeps for a short time
            async def cleanup_delay():
                await asyncio.sleep(0.5)
            
            # Run the cleanup delay task
            loop.run_until_complete(cleanup_delay())
        except Exception as e:
            print(f"Cleanup delay error (can be ignored): {e}")
        
        # Force garbage collection to clean up any remaining resources
        import gc
        gc.collect()
        
        # Close the loop
        loop.close()
