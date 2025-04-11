"""Demo script for the ReAct agent using OpenRouter models with MCP server integration."""
import os
import sys
import json
from typing import Dict, Callable, Tuple
from dotenv import load_dotenv
from react_agent import ReActAgent
from mcp_client import MCPClient

def main():
    """Run a demo of the ReAct agent with MCP tools."""
    # Load environment variables
    load_dotenv()
    
    # Check if API key is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is not set.")
        print("Please create a .env file with your OpenRouter API key.")
        print("You can get an API key at https://openrouter.ai/keys")
        return
    
    print("\n=== Starting MCP Servers ===\n")
    # Use absolute path to mcp_config.json
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_config.json")
    
    # Initialize MCP client
    mcp_client = MCPClient(config_path)
    
    # Start all servers
    mcp_client.start_all_servers()
    
    # Display server status
    print("\n=== MCP Server Status ===\n")
    print(mcp_client.format_status_table())
    
    # Get all MCP tools - only includes tools for servers that are actually running
    tools = mcp_client.get_tools()
    
    if not tools:
        print("\nNo MCP servers are running. Exiting.")
        return
    
    # Available models
    models = {
        "1": "anthropic/claude-3.7-sonnet",
        "2": "anthropic/claude-3-sonnet:beta",
        "3": "google/gemini-2.5-pro-exp-03-25:free",
        "4": "google/gemini-2.5-pro-preview-03-25",
        "5": "openai/gpt-4.5-preview",
        "6": "openai/gpt-4o-mini",
        "7": "meta-llama/llama-3-70b-instruct"
    }
    
    # Let user select a model
    print("\n=== Available Models ===\n")
    for key, model in models.items():
        print(f"{key}: {model}")
    
    # Use a default model to avoid input issues
    model_choice = "1"  # Default to Claude 3.7 Sonnet
    selected_model = models[model_choice]
    print(f"\nAutomatically using model: {selected_model}")
    print("Debug: After model selection")
    
    # Create the agent with a timeout
    try:
        print("\nInitializing ReAct agent...")
        print("Debug: Number of tools available:", len(tools))
        print("Debug: Tool keys:", list(tools.keys()))
        print("Debug: About to create ReActAgent...")
        agent = ReActAgent(tools, model=selected_model)
        print("Debug: ReAct agent initialized successfully.")
    except Exception as e:
        print(f"\nError initializing ReAct agent: {str(e)}")
        print("Shutting down MCP servers...")
        mcp_client.stop_all_servers()
        print("Done!")
        return
    
    # Show which MCP servers are active
    print("\n=== Active MCP Servers ===\n")
    server_status = mcp_client.get_server_status()
    for server, status in server_status.items():
        if "Running" in status:
            print(f"[OK] {server}: Active and running")
        else:
            print(f"[FAILED] {server}: Not available")
    
    # Example questions to try
    example_questions = [
        "What files are in the C:/Code/AIBrowser directory?",
        "Read the file C:/Code/AIBrowser/README.md",
        "Search the knowledge graph for 'Python'",
        "Take a screenshot of the current page",
        "Browse the website https://openrouter.ai",
    ]
    
    print("\n=== Example Questions ===\n")
    for i, question in enumerate(example_questions, 1):
        print(f"{i}: {question}")
    print("C: Custom question")
    
    # Use a default question to avoid input issues
    question = example_questions[0]
    print(f"\nAutomatically using question: {question}")
    
    print(f"\nQuestion: {question}")
    
    # Run the agent with a timeout
    print(f"\nRunning agent with question: {question}")
    try:
        import threading
        import queue
        
        # Create a queue to store the result
        result_queue = queue.Queue()
        
        # Define a function to run the agent and put the result in the queue
        def run_agent():
            try:
                result = agent.run(question)
                result_queue.put((True, result))
            except Exception as e:
                result_queue.put((False, str(e)))
        
        # Start the agent in a separate thread
        agent_thread = threading.Thread(target=run_agent)
        agent_thread.daemon = True
        agent_thread.start()
        
        # Wait for the agent to finish or timeout
        timeout = 60  # 60 seconds timeout
        agent_thread.join(timeout)
        
        if agent_thread.is_alive():
            # Agent is still running after timeout
            print(f"\nAgent timed out after {timeout} seconds.")
            response = "The agent timed out. This could be due to connectivity issues with the MCP servers."
        else:
            # Agent finished, get the result from the queue
            success, result = result_queue.get(block=False)
            if success:
                response = result
            else:
                print(f"\nError running agent: {result}")
                response = f"Error: {result}"
    except Exception as e:
        print(f"\nError running agent: {str(e)}")
        response = f"Error: {str(e)}"
    
    print("\n=== Agent Response ===\n")
    print(response)
    
    # Clean up
    print("\nShutting down MCP servers...")
    mcp_client.stop_all_servers()
    print("Done!")

if __name__ == "__main__":
    main()
