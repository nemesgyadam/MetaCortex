"""
FastAPI server for MetaCortex ReActAgent.
Provides a REST API to interact with the agent.
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from react_agent import ReActAgent, OpenRouterAgent
from functools import partial

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Set root logger to ERROR to catch all other loggers
logging.getLogger().setLevel(logging.ERROR)

# Get API server logger
logger = logging.getLogger("metacortex.api")

# Set all specific loggers to ERROR level
logging.getLogger("uvicorn").setLevel(logging.ERROR)
logging.getLogger("fastapi").setLevel(logging.ERROR)
logging.getLogger("mcp").setLevel(logging.ERROR)
logging.getLogger("playwright").setLevel(logging.ERROR)
logging.getLogger("filesystem").setLevel(logging.ERROR)
logging.getLogger("client_manager").setLevel(logging.ERROR)

# Define lifespan context manager for app startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize resources when the API server starts
    logger.info("Starting MetaCortex API server")
    
    # We'll initialize the agent on first task instead of at startup
    # This avoids event loop conflicts with FastAPI
    
    yield
    
    # Shutdown: Clean up resources when the API server shuts down
    logger.info("Shutting down MetaCortex API server")
    
    # Clean up all active agents
    for agent_id, agent in active_agents.items():
        try:
            if agent is not None:
                agent.cleanup()
                logger.info(f"Cleaned up agent {agent_id}")
        except Exception as e:
            logger.error(f"Error cleaning up agent {agent_id}: {str(e)}")

# Create FastAPI app with lifespan
app = FastAPI(
    title="MetaCortex API",
    description="API for interacting with the MetaCortex ReActAgent",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class TaskRequest(BaseModel):
    """Request model for submitting a task to the agent."""
    query: str = "What files are in C:/Code?"

class TaskResponse(BaseModel):
    """Response model for task results."""
    task_id: str
    result: str
    status: str

# Store for active agents and tasks
active_agents: Dict[str, ReActAgent] = {}
task_results: Dict[str, Dict[str, Any]] = {}

def initialize_agent(task_id: Optional[str] = None) -> ReActAgent:
    """
    Initialize a new ReActAgent instance for the API server.
    Uses the agent's built-in initialization.
    
    Args:
        task_id: Optional task ID to associate with this agent for logging purposes
        
    Returns:
        An initialized ReActAgent
    """
    # Get the config paths (using default will be fine too)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "mcp_config.json")
    project_dir = os.path.dirname(base_dir)
    agent_config_path = os.path.join(project_dir, "prompts", "agents.yaml")
    
    # Setup log file path if task_id is provided
    log_file_path = None
    if task_id:
        thought_processes_dir = os.path.join(project_dir, "thought_processes")
        os.makedirs(thought_processes_dir, exist_ok=True)
        log_file_path = os.path.join(thought_processes_dir, f"{task_id}.txt")
    
    # IMPORTANT: Set the policy for the child watcher which is required for proper subprocess management in asyncio
    # This is the key difference between running directly vs. in FastAPI
    import asyncio
    if sys.platform != 'win32':
        # For non-Windows platforms
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    else:
        # For Windows, ensure we're using the ProactorEventLoop
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Create the agent with basic configuration
    logger.info("Creating new ReActAgent for API server")
    agent = ReActAgent(
        agent_name="APIAgent",
        config_path=config_path,
        agent_config_path=agent_config_path,
        verbose=False,
        concise_mode=False,
        log_file_path=log_file_path
    )
    
    try:
        # Use the agent's built-in initialization with a generous timeout
        logger.info("Initializing agent with built-in method")
        agent.initialize(timeout=20.0)
        
        # Verify connected servers
        if not hasattr(agent, 'client_manager') or not agent.client_manager:
            logger.error("Client manager not initialized")
            raise RuntimeError("Client manager not initialized")
            
        # Log connected servers
        for server_name in agent.client_manager.get_server_names():
            is_connected = agent.client_manager.is_connected(server_name)
            logger.info(f"Server {server_name} connected: {is_connected}")
            
            # If not connected, try to reconnect
            if not is_connected and server_name in agent.client_manager.clients:
                logger.warning(f"Attempting to reconnect to {server_name}")
                try:
                    # Use the agent's event loop for reconnection
                    agent.loop.run_until_complete(
                        agent.client_manager.clients[server_name].connect_to_server()
                    )
                    # Verify reconnection
                    if agent.client_manager.is_connected(server_name):
                        logger.info(f"Successfully reconnected to {server_name}")
                    else:
                        logger.error(f"Failed to reconnect to {server_name}")
                except Exception as reconnect_error:
                    logger.error(f"Error reconnecting to {server_name}: {reconnect_error}")
        
        if not hasattr(agent, 'actions') or not agent.actions:
            logger.warning("No tools available after initialization")
        elif "filesystem.list_directory" not in agent.actions:
            logger.warning("Filesystem server not connected or list_directory tool not available")
            logger.info(f"Available actions: {list(agent.actions.keys())}")
        else:
            logger.info(f"Successfully connected with {len(agent.actions)} tools available")
            
        logger.info("Agent initialization completed successfully")
        return agent
    except Exception as e:
        logger.error(f"Error initializing agent: {str(e)}")
        try:
            # Clean up if initialization fails
            agent.cleanup()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup after failed initialization: {str(cleanup_error)}")
        raise

def process_task(task_id: str, query: str) -> None:
    """
    Process a task with the ReActAgent.
    
    Args:
        task_id: Unique identifier for the task
        query: The query to process
    """
    try:
        # Ensure we have a global agent
        if "global_agent" not in active_agents or active_agents["global_agent"] is None:
            logger.info(f"Global agent not found, initializing a new one for task {task_id}")
            active_agents["global_agent"] = initialize_agent(task_id=task_id)
        
        agent = active_agents["global_agent"]
        
        # Update task status
        task_results[task_id] = {
            "status": "processing",
            "result": ""
        }
        
        # Process the query using the global agent
        logger.info(f"Processing task {task_id} with global agent: {query}")
        
        # Verify agent is initialized
        if not agent.initialized:
            logger.error("Agent not properly initialized")
            raise ValueError("Agent not properly initialized")
        
        # Simply call the agent's run method directly
        result = agent.run(query)
        
        # Store the result
        task_results[task_id] = {
            "status": "completed",
            "result": result
        }
        
        logger.info(f"Completed task {task_id}")
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}")
        
        # Handle agent failures by attempting to re-initialize
        if "Server filesystem is not connected" in str(e):
            logger.warning("Filesystem server connection issue detected. Will attempt to reinitialize agent on next task.")
            try:
                # Clean up the problematic agent
                if "global_agent" in active_agents and active_agents["global_agent"] is not None:
                    active_agents["global_agent"].cleanup()
                # Mark for reinitialization
                active_agents["global_agent"] = None
            except Exception as cleanup_e:
                logger.error(f"Error during agent cleanup after connection failure: {cleanup_e}")
        
        task_results[task_id] = {
            "status": "error",
            "result": f"Error: {str(e)}"
        }



@app.post("/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    """
    Create a new task for the agent to process.
    
    Args:
        task_request: The task request containing the query
        background_tasks: FastAPI background tasks
    
    Returns:
        Task response with task ID and initial status
    """
    # Generate a unique timestamp-based task ID
    import uuid
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    # Initialize task status
    task_results[task_id] = {
        "status": "queued",
        "result": ""
    }
    
    # Process the task in the background
    def process_task_wrapper(tid: str, q: str):
        try:
            process_task(tid, q)
        except Exception as e:
            logger.error(f"Error in task wrapper for {tid}: {e}")
            # Ensure the task result is updated even if process_task fails completely
            task_results[tid] = {
                "status": "error",
                "result": f"Error processing task: {str(e)}"
            }
    
    background_tasks.add_task(process_task_wrapper, task_id, task_request.query)
    
    logger.info(f"Created new task {task_id} with query: {task_request.query}")
    
    return TaskResponse(
        task_id=task_id,
        result="",
        status="queued"
    )

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """
    Get the status and result of a task.
    
    Args:
        task_id: The ID of the task to retrieve
    
    Returns:
        Task response with current status and result
    """
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    task_info = task_results[task_id]
    
    return TaskResponse(
        task_id=task_id,
        result=task_info.get("result", ""),
        status=task_info.get("status", "unknown")
    )

@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks() -> List[TaskResponse]:
    """
    List all tasks and their statuses.
    
    Returns:
        List of task responses
    """
    return [
        TaskResponse(
            task_id=task_id,
            result=task_info.get("result", ""),
            status=task_info.get("status", "unknown")
        )
        for task_id, task_info in task_results.items()
    ]

@app.get("/tasks/{task_id}/thought-process", response_class=PlainTextResponse)
async def get_thought_process(task_id: str) -> str:
    """
    Get the thought process logs for a specific task.
    
    Args:
        task_id: The ID of the task to retrieve thought process for
    
    Returns:
        Plain text content of the thought process file
    """
    # First check if task exists
    #if task_id not in task_results:
    #    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    # Construct path to thought process file
    
    project_dir = "C:\Code\MetaCortex_v1"
    thought_process_path = os.path.join(project_dir, "thought_processes", f"{task_id}.txt")
    #print(thought_process_path)
    # Check if thought process file exists
    if not os.path.exists(thought_process_path):
        raise HTTPException(status_code=404, detail=f"Thought process file for task {task_id} not found")
    
    try:
        # Read file content
        with open(thought_process_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
    except Exception as e:
        logger.error(f"Error reading thought process file for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading thought process file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="error",
        access_log=False,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(message)s",
                    "use_colors": True,
                }
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                }
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "ERROR"},
                "uvicorn.error": {"handlers": ["default"], "level": "ERROR"},
                "uvicorn.access": {"handlers": ["default"], "level": "ERROR", "propagate": False},
            }
        }
    )
