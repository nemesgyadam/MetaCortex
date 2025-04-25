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
import time
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, Tuple, Union
from pathlib import Path
from enum import Enum
from colorama import Fore, Back, Style, init
from dotenv import load_dotenv
from client_manager import ClientManager
from agent_config import AgentConfig

# Initialize colorama for cross-platform colored terminal output
init(autoreset=True)

# Load environment variables
load_dotenv()

# Constants
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TIMEOUT = 30.0
DEFAULT_MAX_TOKENS = 1000
DEFAULT_MODEL = "anthropic/claude-3-opus:beta"
DEFAULT_ENDURANCE = 5
CLEANUP_DELAY_SECONDS = 0.5

# Regex patterns
ACTION_PATTERN = r'Action: \[([^|]+)\|(.*)\]'

# File paths
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = BASE_DIR.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "mcp_config.json"
DEFAULT_AGENT_CONFIG_PATH = PROJECT_DIR / "prompts" / "agents.yaml"
DEFAULT_PROMPT_PATH = PROJECT_DIR / "prompts" / "react_agent.txt"


class LogLevel(Enum):
    """Log levels for agent operations with associated colors."""
    DEBUG = (Fore.CYAN, "DEBUG")
    INFO = (Fore.GREEN, "INFO")
    ACTION = (Fore.BLUE, "ACTION")
    THOUGHT = (Fore.MAGENTA, "THOUGHT")
    OBSERVATION = (Fore.YELLOW, "OBSERVATION")
    RESPONSE = (Fore.WHITE, "RESPONSE")
    WARNING = (Fore.YELLOW, "WARNING")
    ERROR = (Fore.RED, "ERROR")
    CRITICAL = (Fore.RED + Back.WHITE, "CRITICAL")
    SUCCESS = (Fore.GREEN + Style.BRIGHT, "SUCCESS")


class AgentLogger:
    """Fancy console logger for agent operations with colored output and formatting."""
    
    def __init__(self, agent_name: str = "ReActAgent", show_timestamps: bool = True, concise_mode: bool = False):
        """
        Initialize the agent logger.
        
        Args:
            agent_name: Name of the agent for log prefixing
            show_timestamps: Whether to include timestamps in log messages
            concise_mode: If True, only show essential logs (THOUGHT, ACTION, OBSERVATION, RESPONSE, ERROR, CRITICAL, SUCCESS)
        """
        self.agent_name = agent_name
        self.show_timestamps = show_timestamps
        self.concise_mode = concise_mode
        self.start_time = time.time()
        self.step_count = 0
        
        # Define which log levels to show in concise mode
        self.concise_log_levels = [
            LogLevel.THOUGHT,
            LogLevel.ACTION,
            LogLevel.OBSERVATION,
            LogLevel.RESPONSE,
            LogLevel.ERROR,
            LogLevel.CRITICAL,
            LogLevel.SUCCESS
        ]
        
    def _get_timestamp(self) -> str:
        """
        Get a formatted timestamp string.
        
        Returns:
            Formatted timestamp
        """
        if self.show_timestamps:
            return f"[{datetime.now().strftime('%H:%M:%S')}] "
        return ""
        
    def _format_step(self) -> str:
        """
        Format the step count with elapsed time.
        
        Returns:
            Formatted step count with elapsed time
        """
        elapsed = time.time() - self.start_time
        return f"Step {self.step_count} ({elapsed:.2f}s): "
        
    def log(self, message: str, level: LogLevel = LogLevel.INFO, increment_step: bool = False) -> None:
        """
        Log a message with the specified level and formatting.
        
        Args:
            message: The message to log
            level: The log level to use for formatting
            increment_step: Whether to increment the step counter
        """
        # In concise mode, skip logs that aren't in the concise_log_levels list
        if self.concise_mode and level not in self.concise_log_levels:
            return
            
        color, label = level.value
        
        if increment_step:
            self.step_count += 1
            
        timestamp = self._get_timestamp()
        step_info = self._format_step() if self.step_count > 0 else ""
        
        # Format the output with color and structure
        print(f"{timestamp}{color}[{self.agent_name}] {Style.BRIGHT}{label}{Style.RESET_ALL}{color} {step_info}{message}")
        
    def section(self, title: str) -> None:
        """
        Print a section divider with a title.
        
        Args:
            title: The section title
        """
        # In concise mode, only show FINAL ANSWER section headers
        if self.concise_mode and title != "FINAL ANSWER":
            return
            
        width = 80
        padding = (width - len(title) - 4) // 2
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'-' * padding} {title} {'-' * padding}{Style.RESET_ALL}\n")
        
    def divider(self) -> None:
        """Print a simple divider line."""
        print(f"\n{Fore.CYAN}{'-' * 80}{Style.RESET_ALL}\n")
        
    def thought(self, message: str) -> None:
        """Log an agent thought."""
        self.log(message, LogLevel.THOUGHT, increment_step=True)
        
    def action(self, server: str, tool: str, args: Dict[str, str]) -> None:
        """Log an agent action with its components."""
        args_str = ", ".join([f"{k}={v}" for k, v in args.items()])
        self.log(f"Tool: {server}|{tool}({args_str})", LogLevel.ACTION, increment_step=True)
        
    def observation(self, message: str) -> None:
        """Log an observation from a tool call."""
        self.log(f"Result: {message}", LogLevel.OBSERVATION)
        
    def response(self, message: str) -> None:
        """Log an agent response."""
        self.log(message, LogLevel.RESPONSE)
        
    def final_answer(self, message: str) -> None:
        """Log the final answer with special formatting."""
        self.section("FINAL ANSWER")
        self.log(message, LogLevel.SUCCESS)

class OpenRouterAgent:
    """ReAct agent using OpenRouter API to access various LLM models."""
    
    def __init__(self, system_prompt: str = "", model: str = DEFAULT_MODEL):
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
        self._async_client = None
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
            
        if self.system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
    
    async def __call__(self, message: str) -> str:
        """
        Process a user message and return the agent's response asynchronously.
        
        Args:
            message: User message to process
            
        Returns:
            Agent's response
        """
        self.messages.append({"role": "user", "content": message})
        result = await self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """
        Create and return an async HTTP client for API requests.
        
        Returns:
            Configured async HTTP client
        """
        return httpx.AsyncClient(
            timeout=OPENROUTER_TIMEOUT,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    def _prepare_payload(self) -> Dict[str, Any]:
        """
        Prepare the request payload for the OpenRouter API.
        
        Returns:
            Dictionary containing the API request payload
        """
        return {
            "model": self.model,
            "messages": self.messages,
            "max_tokens": DEFAULT_MAX_TOKENS
        }
    
    async def _handle_api_response(self, response: httpx.Response) -> str:
        """
        Process the API response and extract the model's output.
        
        Args:
            response: HTTP response from the API
            
        Returns:
            Extracted model output or error message
        """
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
    
    async def execute(self) -> str:
        """
        Execute the API call to OpenRouter asynchronously.
        
        Returns:
            Model's response content
        """
        if self._async_client is None:
            self._async_client = self._create_http_client()
        
        try:
            payload = self._prepare_payload()
            response = await self._async_client.post(OPENROUTER_API_URL, json=payload)
            return await self._handle_api_response(response)
            
        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            print(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Error during API call: {str(e)}"
            print(error_msg)
            return f"Error: {error_msg}"
    
    async def cleanup(self) -> None:
        """
        Clean up resources used by the agent.
        """
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None


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
        agent_config_path: str = None,
        agent_name: str = None,
        verbose: bool = True,
        concise_mode: bool = False
    ):
        """
        Initialize the ReAct agent.
        
        Args:
            model: OpenRouter model identifier to use (overrides agent config if provided)
            endurance: Indicate the maximum number of reasoning turns before giving up (overrides agent config if provided)
            config_path: Path to MCP configuration file
            agent_config_path: Path to agent configuration YAML file
            agent_name: Custom name for the agent (used in logging)
            verbose: Whether to output detailed logs
            concise_mode: If True, only show essential logs (THOUGHT, ACTION, OBSERVATION, RESPONSE, ERROR, CRITICAL, SUCCESS)
        """
        # Initialize with paths
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.agent_config_path = Path(agent_config_path) if agent_config_path else DEFAULT_AGENT_CONFIG_PATH
        
        # Configure logging
        self.verbose = verbose
        self.concise_mode = concise_mode
        self.logger = AgentLogger(agent_name or "ReActAgent", show_timestamps=True, concise_mode=concise_mode)
        
        # These will be populated during initialization
        self.client_manager = None
        self.agent_config = None
        self.agent_data = {}
        self.actions = {}
        self.system_prompt = ""
        self.llm_agent = None
        self.initialized = False
        
        # Initialize agent configuration data
        self._initialize_config_data(model, endurance)
        
        # Log startup info
        self.logger.log(f"Initialized with model={self.model}, endurance={self.endurance}", LogLevel.INFO)
    
    def _initialize_config_data(self, model: Optional[str] = None, endurance: Optional[int] = None) -> None:
        """
        Initialize the agent configuration data from the config file or defaults.
        
        Args:
            model: OpenRouter model identifier (overrides config)
            endurance: Maximum reasoning turns (overrides config)
        """
        # Create client manager with provided config path
        # Pass verbose=False to hide MCP-related logs
        self.client_manager = ClientManager(str(self.config_path), verbose=False)
        
        # Load agent configuration
        self.agent_config = AgentConfig(str(self.agent_config_path))
        self.agent_data = self.agent_config.get_agent_config("assistant_agent")
        
        # Set model from config or default
        self.model = model or self.agent_data.get("model", "openai/gpt-4o").strip()
        
        # Parse endurance from config if not provided directly
        self.endurance = self._parse_endurance(endurance)
        self.max_turns = self.endurance**2
        
        # Compile regex pattern for action extraction
        self.action_re = re.compile(ACTION_PATTERN)
        
        # Set agent persona attributes
        self.role = self.agent_data.get("role", "").strip()
        self.goal = self.agent_data.get("goal", "").strip()
        self.backstory = self.agent_data.get("backstory", "").strip()
    
    def _parse_endurance(self, endurance: Optional[int] = None) -> int:
        """
        Parse endurance from config or use default.
        
        Args:
            endurance: Provided endurance value
            
        Returns:
            Parsed endurance value or default
        """
        if endurance is not None:
            return endurance
            
        config_endurance = self.agent_data.get("endurance")
        if config_endurance:
            try:
                return int(config_endurance.strip())
            except (ValueError, TypeError):
                pass
                
        return DEFAULT_ENDURANCE
    
    async def _load_system_prompt(self) -> None:
        """
        Load the system prompt from the prompt file and format it with action descriptions.
        """
        # Create a description of all available actions for the system prompt
        action_list = list(self.actions.items())
        action_descriptions = "\n".join([
            f"- {name}: {description}" 
            for name, (_, description) in action_list
        ])
        
        if self.verbose:
            self.logger.log(f"Available actions ({len(action_list)}):", LogLevel.DEBUG)
            for name, (_, description) in action_list:
                self.logger.log(f"  - {name}: {description}", LogLevel.DEBUG)
        
        try:
            # Load prompt template from file
            prompt_path = DEFAULT_PROMPT_PATH
            self.logger.log(f"Loading prompt from {prompt_path}", LogLevel.INFO)
            with open(prompt_path, 'r') as f:
                prompt_template = f.read()
            
            # Replace tags with values
            self.system_prompt = prompt_template.replace("{{action_descriptions}}", action_descriptions)
            
            # Add agent persona
            self._add_agent_persona()
            self.logger.log("Prompt loaded and configured with agent persona", LogLevel.SUCCESS)
            
        except Exception as e:
            self.logger.log(f"Error loading system prompt: {str(e)}", LogLevel.ERROR)
            raise ValueError(f"Error loading system prompt: {str(e)}")
    
    def _add_agent_persona(self) -> None:
        """
        Add agent persona details (role, goal, backstory) to the system prompt.
        """
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
    
    async def _parse_action_args(self, action_args: Optional[str]) -> Dict[str, Any]:
        """
        Parse action arguments from a string into a dictionary.
        Handles potential multiple colons in values and attempts type conversion.
        
        Args:
            action_args: String containing action arguments (e.g., "lat:47.5,lon:19.1,note:city:center")
            
        Returns:
            Dictionary of parsed arguments with potential type conversion.
        """
        args = {}
        if not action_args:
            return args
        
        # Split parameters by comma
        param_pairs = action_args.split(',') 
        for pair in param_pairs:
            # Split each parameter into key and value by the FIRST colon only
            key_value = pair.split(':', 1)
            if len(key_value) == 2:
                key = key_value[0].strip()
                value_str = key_value[1].strip()
                # Attempt to convert value to float or int, otherwise keep as string
                try:
                    # Prioritize float conversion for lat/lon type values
                    value = float(value_str)
                    # Convert to int if it's a whole number
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    value = value_str # Keep as string if conversion fails
                args[key] = value
            elif len(key_value) == 1 and key_value[0].strip(): # Handle case of key with no value?
                 # Decide how to handle keys without values (e.g., flags)
                 # Option 1: Assign a default value (e.g., True)
                 # args[key_value[0].strip()] = True 
                 # Option 2: Log a warning/error
                 self.logger.log(f"Parameter '{key_value[0].strip()}' has no value.", LogLevel.WARNING)
                 # Option 3: Ignore it (current behavior by not adding to dict)
                 pass
            # Implicitly ignore empty strings resulting from trailing commas, etc.
            
        return args
    
    async def _process_llm_response(self, response: str, current_prompt: str) -> Tuple[str, bool]:
        """
        Process the LLM's response to identify final answers or actions.
        
        Args:
            response: The LLM's response to process
            current_prompt: The current conversation prompt
            
        Returns:
            Tuple of (next_prompt, is_final_answer)
        """
        # Check if we have a final answer
        if "Final answer:" in response:
            return response, True
        
        # Check if we have an action to perform
        action_match = self.action_re.search(response)
        if not action_match:
            self.logger.response(response)
            self.logger.log("No action detected in response", LogLevel.INFO)
            return current_prompt, False
            
        # Extract action components
        full_tool_name = action_match.group(1).strip() # Get full tool name (e.g., "wolt.list_italian_restaurants")
        params_str = action_match.group(2).strip()     # Get raw parameters string (e.g., "lat:47.4979937,lon:19.0403594")

        # Split tool name (assuming format server.action)
        try:
            server_name, action_name = full_tool_name.split('.', 1)
        except ValueError:
            # Handle cases where the tool name doesn't contain a '.' separator
            self.logger.log(f"Could not split tool name '{full_tool_name}' into server and action.", LogLevel.ERROR)
            # Depending on desired behavior, you might want to raise an error or return differently
            return current_prompt, False
        
        # Parse arguments using the raw parameter string
        args = await self._parse_action_args(params_str)
        
        # Log the action being taken
        self.logger.action(server_name, action_name, args)
        
        # Call the action
        try:
            result = await self.client_manager.call_tool(server_name, action_name, args)
            # Log the observation
            self.logger.observation(result)
        except Exception as e:
            error_msg = f"Error executing tool {server_name}.{action_name}: {str(e)}"
            self.logger.log(error_msg, LogLevel.ERROR)
            result = f"Error: {error_msg}"
            self.logger.observation(result)
        
        # Update prompt with observation
        next_prompt = f"{current_prompt}\r\nObservation: {result}"
        return next_prompt, False
    
    def initialize(self, timeout: float = 10.0) -> None:
        """
        Initialize the ReAct agent. Uses existing event loop if available, otherwise creates one.
        This needs to be called before using the agent.
        
        Args:
            timeout: Maximum time in seconds to wait for initialization of each attempt
        """
        self.logger.section("INITIALIZING AGENT")
        
        # Try to get existing event loop, create new one if none exists
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        # Run the async initialization in our loop with retry mechanism
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Create a task with timeout
                async def init_with_timeout():
                    await self._async_initialize()
                    # Verify filesystem server connection
                    if not self.client_manager or not self.client_manager.is_connected("filesystem"):
                        raise RuntimeError("Filesystem server not connected after initialization")
                
                # Run initialization with timeout
                self.loop.run_until_complete(asyncio.wait_for(init_with_timeout(), timeout))
                self.logger.log(f"Agent initialized successfully on attempt {attempt + 1}", LogLevel.SUCCESS)
                return
            except asyncio.TimeoutError:
                last_error = RuntimeError(f"Initialization timed out after {timeout} seconds")
                self.logger.log(f"Initialization attempt {attempt + 1} timed out", LogLevel.WARNING)
            except Exception as e:
                last_error = e
                self.logger.log(f"Initialization attempt {attempt + 1} failed: {e}", LogLevel.WARNING)
            
            # Retry logic
            if attempt < max_retries - 1:
                self.logger.log(f"Retrying initialization... ({attempt + 2}/{max_retries})", LogLevel.INFO)
                # Small delay before retry
                self.loop.run_until_complete(asyncio.sleep(1.0))
                # Clean up before retry
                if self.client_manager:
                    self.loop.run_until_complete(self.client_manager.close_all_clients())
                    self.client_manager = ClientManager(self.config_path, verbose=self.verbose)
                # Wait a bit before retrying
                self.loop.run_until_complete(asyncio.sleep(1.0))
        
        self.logger.log(f"Failed to initialize after {max_retries} attempts: {last_error}", LogLevel.ERROR)
        raise last_error
    
    def is_connected(self, server_name: str) -> bool:
        """
        Check if a specific server is connected.
        
        Args:
            server_name: Name of the server to check
            
        Returns:
            bool: True if server is connected, False otherwise
        """
        if not self.clients:
            return False
        return server_name in self.clients and self.clients[server_name] is not None
    
    async def _async_initialize(self) -> None:
        """
        Initialize the ReAct agent asynchronously.
        Internal method used by initialize().
        """
        if self.initialized:
            self.logger.log("Agent already initialized", LogLevel.INFO)
            return
            
        # Start client manager and connect to servers
        self.logger.log("Starting client manager", LogLevel.INFO)
        await self.client_manager.start()
        
        # Verify that critical servers are connected
        self.logger.log("Verifying server connections", LogLevel.INFO)
        if not self.client_manager.is_connected("filesystem"):
            self.logger.log("Filesystem server not connected", LogLevel.ERROR)
            raise RuntimeError("Failed to connect to filesystem server")
            
        # Ensure we have access to the connected clients
        if not hasattr(self.client_manager, 'connected_clients') or not self.client_manager.connected_clients:
            self.logger.log("No connected clients available", LogLevel.ERROR)
            for server_name in self.client_manager.get_server_names():
                self.logger.log(f"Server {server_name} connection status: {self.client_manager.is_connected(server_name)}", LogLevel.INFO)
            
        # Get tools from all connected clients
        self.logger.log("Loading available tools", LogLevel.INFO)
        self.actions = self.client_manager.get_tools()
        
        # Debug output of available tools
        if not self.actions:
            self.logger.log("No tools loaded - debugging connection state:", LogLevel.WARNING)
            for server_name, client in self.client_manager.connected_clients.items():
                if hasattr(client, 'tools'):
                    self.logger.log(f"Server {server_name} has {len(client.tools)} tools", LogLevel.INFO)
                else:
                    self.logger.log(f"Server {server_name} has no tools attribute", LogLevel.WARNING)
        else:
            self.logger.log(f"Loaded {len(self.actions)} tools", LogLevel.INFO)
        
        # Load system prompt with action descriptions
        self.logger.log("Loading system prompt", LogLevel.INFO)
        await self._load_system_prompt()
        
        # Create the LLM agent with our prompt and model
        self.logger.log(f"Creating LLM agent with model {self.model}", LogLevel.INFO)
        self.llm_agent = OpenRouterAgent(system_prompt=self.system_prompt, model=self.model)
        
        self.initialized = True
    
    def run(self, question: str) -> str:
        """
        Run the ReAct agent on a question. Creates and manages its own event loop.
        
        Args:
            question: The question to answer
            
        Returns:
            Final answer after the reasoning process
        """
        # Verify initialization
        if not self.initialized:
            self.initialize()
            
        # Log the question
        self.logger.section("NEW TASK")
        self.logger.log(f"Question: {question}", LogLevel.INFO)
            
        # Run the async method in our loop
        try:
            result = self.loop.run_until_complete(self._async_run(question))
            return result
        except Exception as e:
            self.logger.log(f"Error during run: {e}", LogLevel.ERROR)
            raise
    
    async def _async_run(self, question: str) -> str:
        """
        Run the ReAct agent on a question asynchronously.
        Internal method used by run().
        
        Args:
            question: The question to answer
            
        Returns:
            Final answer after the reasoning process
        """
        # Initialize conversation
        turn = 0
        current_prompt = question
        
        # Reset the step counter for this run
        self.logger.step_count = 0
        self.logger.start_time = time.time()
        
        # Run the agent loop
        while turn < self.max_turns:
            turn += 1
            self.logger.section(f"TURN {turn}/{self.max_turns}")
            
            # Get response from LLM
            self.logger.log("Generating response...", LogLevel.INFO)
            response = await self.llm_agent(current_prompt)
            
            # Extract thought content if present
            thought_match = re.search(r'Thought: (.*?)(?:\r\n|\n|$)', response)
            if thought_match:
                thought = thought_match.group(1).strip()
                self.logger.thought(thought)
            
            # Process the response to find actions or final answers
            next_prompt, is_final = await self._process_llm_response(response, current_prompt)
            
            # Return if we have a final answer
            if is_final:
                final_answer_match = re.search(r'Final answer: (.*)', response, re.DOTALL)
                if final_answer_match:
                    final_answer = final_answer_match.group(1).strip()
                    self.logger.final_answer(final_answer)
                else:
                    self.logger.final_answer(response)
                return response
                
            # Update for next iteration
            current_prompt = next_prompt
        
        msg = "Reached maximum number of turns without a final answer."
        self.logger.log(msg, LogLevel.WARNING)
        return msg
    
    def cleanup(self) -> None:
        """
        Clean up resources when the agent is done.
        """
        self.logger.section("CLEANUP")
        self.logger.log("Cleaning up resources...", LogLevel.INFO)
        
        try:
            self.loop.run_until_complete(self._async_cleanup())
        except Exception as e:
            self.logger.log(f"Error during cleanup: {e}", LogLevel.ERROR)
        finally:
            # Process any pending tasks
            self.logger.log("Processing pending tasks", LogLevel.DEBUG)
            self._process_pending_tasks()
            self._close_event_loop()
            self.logger.log("Cleanup completed", LogLevel.SUCCESS)
    
    def _process_pending_tasks(self) -> None:
        """
        Process any pending tasks by cancelling them and letting them complete.
        """
        try:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                if not task.done():
                    task.cancel()
            
            # Allow the loop to process the cancellations
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            print(f"Error processing pending tasks: {e}")
    
    def _close_event_loop(self) -> None:
        """
        Close the event loop and perform final cleanup.
        """
        try:
            # Run a small delay to allow resources to be properly released
            async def cleanup_delay():
                await asyncio.sleep(CLEANUP_DELAY_SECONDS)
                
            self.loop.run_until_complete(cleanup_delay())
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Close the loop
            self.loop.close()
        except Exception as e:
            print(f"Cleanup error (can be ignored): {e}")
    
    async def _async_cleanup(self) -> None:
        """
        Clean up resources when the agent is done.
        Internal async method used by cleanup().
        """
        try:
            # Clean up the LLM agent if it exists
            if self.llm_agent is not None:
                self.logger.log("Cleaning up LLM agent", LogLevel.DEBUG)
                await self.llm_agent.cleanup()
                self.llm_agent = None
                
            # Close all client connections
            if self.client_manager is not None:
                self.logger.log("Closing MCP client connections", LogLevel.DEBUG)
                await self.client_manager.close_all_clients()
                self.logger.log("All MCP client connections closed", LogLevel.SUCCESS)
                self.client_manager = None
        except Exception as e:
            self.logger.log(f"Error during resource cleanup: {str(e)}", LogLevel.ERROR)
        finally:
            # Reset initialization state
            self.initialized = False





if __name__ == "__main__":
    # Example of using the ReActAgent with fancy colored output
    logger = AgentLogger("Main")
    logger.section("META CORTEX AGENT DEMO")
    
    try:
        # Create the agent with a custom name
        agent_name = "MetaCortexAgent"
        logger.log(f"Creating {agent_name}", LogLevel.INFO)
        agent = ReActAgent(agent_name=agent_name)
        
        # Initialize the agent
        agent.initialize()
        
        # Define a sample question
        question = "What files are in C:/Code?"
        logger.log(f"Running agent with question: '{question}'", LogLevel.INFO)
        
        # Run the agent
        result = agent.run(question)
        
        # Optionally run with an additional question
        # question2 = "What is the weather in New York?"
        # logger.log(f"Running agent with second question: '{question2}'", LogLevel.INFO)
        # result2 = agent.run(question2)
        
    except Exception as e:
        logger.log(f"Error in main: {e}", LogLevel.ERROR)
        import traceback
        logger.log(traceback.format_exc(), LogLevel.DEBUG)
    finally:
        # Make sure to clean up resources
        if 'agent' in locals():
            agent.cleanup()
            logger.section("DEMO COMPLETED")
