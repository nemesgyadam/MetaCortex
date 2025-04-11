"""
Client Manager for MetaCortex
Loads MCP server configurations from JSON files and creates MCP clients for each server.

This module provides a centralized way to manage multiple MCP clients across different
configuration files. It handles the loading of configurations, creation of clients,
connection to servers, and proper cleanup of resources.

Example usage:
    manager = ClientManager()
    await manager.load_configs()
    await manager.create_clients()
    await manager.connect_all_clients()
    
    # Call a tool on a specific server
    result = await manager.call_tool("filesystem", "list_directory", {"path": "C:/Code"})
    
    # Clean up when done
    await manager.close_all_clients()
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Callable
from contextlib import AsyncExitStack

from my_client import MCPClient


class ClientManager:
    """
    Manages multiple MCP clients based on configuration from JSON files.
    Creates and maintains connections to multiple MCP servers.
    """
    
    def __init__(self, config_file_path: Optional[str] = None):
        """
        Initialize the client manager with a configuration file path.
        
        Args:
            config_file_path: Path to the JSON configuration file.
                             If None, defaults to mcp_config.json in the meta_cortex directory.
        """
        # Set default config path if none provided
        if config_file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_file_path = os.path.join(base_dir, "mcp_config.json")
        else:
            self.config_file_path = config_file_path
            
        self.config: Dict[str, Any] = {}  # The loaded configuration
        self.clients: Dict[str, MCPClient] = {}  # server_name -> client
        self.connected_clients: Dict[str, MCPClient] = {}
        
    async def start(self):
        await self.load_config()
        await self.create_clients()
        await self.connect_all_clients()

    async def load_config(self) -> Dict[str, Any]:
        """
        Load the configuration file and parse the MCP server definitions.
        
        Returns:
            The parsed configuration dictionary
        """
        try:
            # Check if file exists
            if not os.path.exists(self.config_file_path):
                print(f"Configuration file {self.config_file_path} does not exist")
                return {}
                
            with open(self.config_file_path, 'r') as f:
                self.config = json.load(f)
                print(f"Loaded MCP configuration from {self.config_file_path}")
                return self.config
        except json.JSONDecodeError:
            print(f"Error parsing JSON in {self.config_file_path}")
            return {}
        except Exception as e:
            print(f"Error loading configuration file {self.config_file_path}: {str(e)}")
            return {}
    
    def get_server_names(self) -> List[str]:
        """
        Get the list of server names from the loaded configuration.
        
        Returns:
            List of server names
        """
        return list(self.config.get("mcpServers", {}).keys())
    
    def get_tools(self) -> Dict[str, Tuple[Callable, str]]:
        """
        Get all available tools from connected clients in a format suitable for the ReAct agent.
        
        Returns:
            Dictionary of tool names to (tool_function, description) tuples
        """
        tools = {}
        
        # For each connected client, get its tools
        for server_name, client in self.connected_clients.items():
            # Create a wrapper function to call the tool on this specific server
            def create_tool_wrapper(server, tool_name):
                def tool_wrapper(input_str):
                    try:
                        print(f"\n[Tool wrapper for {server}_{tool_name} called with input: {input_str}]")
                        
                        # Get the input schema for this tool to determine the correct parameter names
                        input_schema = None
                        for t in client.tools:
                            if t['name'] == tool_name:
                                input_schema = t.get('input_schema', {})
                                break
                        
                        print(f"[Input schema for {tool_name}: {input_schema}]")
                                
                        # Parse the input string as JSON if it's a valid JSON string
                        try:
                            # Try to parse as JSON first
                            input_params = json.loads(input_str)
                            print(f"[Parsed input as JSON: {input_params}]")
                        except json.JSONDecodeError:
                            # If we have an input schema, use the first property as the parameter name
                            if input_schema and isinstance(input_schema, dict) and 'properties' in input_schema:
                                properties = input_schema.get('properties', {})
                                if properties and len(properties) > 0:
                                    # Use the first property name from the schema
                                    first_param_name = next(iter(properties))
                                    input_params = {first_param_name: input_str.strip()}
                                    print(f"[Using schema property '{first_param_name}' for input]")
                                else:
                                    # Fallback to using the raw input string
                                    input_params = {"input": input_str.strip()}
                                    print("[No properties in schema, using 'input' as parameter name]")
                            else:
                                # Fallback to using the raw input string
                                input_params = {"input": input_str.strip()}
                                print("[No schema available, using 'input' as parameter name]")
                        
                        print(f"[Calling tool {tool_name} on server {server} with params: {input_params}]")
                            
                        # Create a new event loop for this call
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            # Call the tool with the properly formatted parameters
                            result = loop.run_until_complete(
                                self.call_tool(server, tool_name, input_params)
                            )
                            print(f"[Tool {tool_name} returned result: {result}]")
                            return result
                        finally:
                            loop.close()
                    except Exception as e:
                        error_msg = f"Error executing {tool_name}: {str(e)}"
                        print(f"[Tool wrapper error: {error_msg}]")
                        return {"error": error_msg}
                return tool_wrapper
            
            # If the client has tools, add them to our tools dictionary
            if hasattr(client, 'tools') and client.tools:
                for tool in client.tools:
                    tool_name = tool['name']
                    tool_description = tool['description']
                    
                    # Create a unique name for the tool that includes the server name
                    unique_tool_name = f"{server_name}|{tool_name}"
                    
                    # Create a wrapper function for this tool
                    tool_func = create_tool_wrapper(server_name, tool_name)
                    
                    # Add the tool to our tools dictionary
                    tools[unique_tool_name] = (tool_func, tool_description)
                    #print(f"Added tool: {unique_tool_name}")
                    
        return tools

    async def create_clients(self) -> Dict[str, MCPClient]:
        """
        Create MCP clients for all servers defined in the configuration.
        
        Returns:
            Dictionary of server names to MCPClient instances
        """
        if not self.config:
            await self.load_config()
        
        server_configs = self.config.get("mcpServers", {})
        
        for server_name, server_config in server_configs.items():
            command = server_config.get("command", "")
            args = server_config.get("args", [])
            
            try:
                client = MCPClient(command=command, args=args)
                self.clients[server_name] = client
                print(f"Created client for server: {server_name}")
            except Exception as e:
                print(f"Error creating client for server {server_name}: {str(e)}")
        
        return self.clients
    
    async def connect_all_clients(self) -> Dict[str, MCPClient]:
        """
        Connect to all MCP servers.
        
        Returns:
            Dictionary of connected server names to MCPClient instances
        """
        # Make sure we have clients
        if not self.clients and not self.config:
            await self.load_config()
            await self.create_clients()
            
        for server_name, client in self.clients.items():
            try:
                await client.connect_to_server()
                self.connected_clients[server_name] = client
                print(f"Connected to server: {server_name}")
            except Exception as e:
                print(f"Error connecting to server {server_name}: {str(e)}")
                
        return self.connected_clients
    
    async def close_all_clients(self) -> None:
        """
        Close all connected clients and clean up resources.
        """
        # Create a list of clients to avoid modifying the dictionary during iteration
        client_items = list(self.clients.items())
        
        # Close each client individually with separate tasks to prevent cancellation propagation
        close_tasks = []
        
        for server_name, client in client_items:
            if hasattr(client, 'exit_stack') and client.exit_stack is not None:
                # Create a task for each client close operation
                task = asyncio.create_task(self._close_client(server_name, client))
                close_tasks.append(task)
            else:
                print(f"Client {server_name} has no exit_stack, skipping close")
        
        # Wait for all close tasks to complete, but don't propagate cancellations
        if close_tasks:
            done, pending = await asyncio.wait(close_tasks, timeout=3.0)
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                
            # Wait for the cancelled tasks to finish (they'll raise CancelledError)
            if pending:
                await asyncio.wait(pending, timeout=1.0)
        
        # Clear the client dictionaries after all closing attempts
        self.clients = {}
        self.connected_clients = {}
        
    async def _close_client(self, server_name: str, client: MCPClient) -> None:
        """
        Helper method to close a single client with proper error handling.
        
        Args:
            server_name: Name of the server
            client: MCPClient instance to close
        """
        try:
            # Use a shield to prevent cancellation from propagating
            await asyncio.shield(client.close())
            print(f"Closed connection to server: {server_name}")
        except asyncio.CancelledError:
            print(f"Closing of {server_name} was cancelled, continuing cleanup")
            # Force cleanup of client resources
            if hasattr(client, 'exit_stack'):
                client.exit_stack = None
            if hasattr(client, 'session'):
                client.session = None
            if hasattr(client, 'stdio'):
                client.stdio = None
            if hasattr(client, 'write'):
                client.write = None
        except Exception as e:
            print(f"Error closing connection to server {server_name}: {str(e)}")
            # Force cleanup of client resources
            if hasattr(client, 'exit_stack'):
                client.exit_stack = None
            if hasattr(client, 'session'):
                client.session = None
            if hasattr(client, 'stdio'):
                client.stdio = None
            if hasattr(client, 'write'):
                client.write = None
    
    async def call_tool(self, server_name: str, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Call a tool on a specific server with the given parameters.
        
        Args:
            server_name: Name of the server to call the tool on
            tool_name: Name of the tool to call
            params: Parameters to pass to the tool
            
        Returns:
            Result of the tool call
        """
        print(f"[Client manager calls tool {tool_name} on server {server_name}]")
        # # Make sure we have connected clients
        # if not self.connected_clients:
        #     await self.connect_all_clients()
            
        if server_name not in self.connected_clients:
            raise ValueError(f"Server {server_name} is not connected")
            
        client = self.connected_clients[server_name]
        
        try:
            print("calling tooooool")
            result = await client.call_tool(tool_name, params)
            return result
        except Exception as e:
            error_msg = f"Error calling tool {tool_name} on server {server_name}: {str(e)}"
            print(error_msg)
            return {"error": error_msg}

async def main():
    """
    Example usage of the ClientManager.
    """
    # Use the default configuration loading (automatically finds all config files)
    manager = ClientManager()
    
 
    try:
        # Load configurations
        await manager.start()
        
        server_names = manager.get_server_names()
        print(f"Available servers: {server_names}")
        
        # Example: Call a tool on the filesystem server if available
        if "filesystem" in server_names:
            result = await manager.call_tool("filesystem", "list_directory", {"path": "C:/Code"})
            print(f"Directory listing result: {result}")
        
    except Exception as e:
        print(f"Error in main: {str(e)}")
    finally:
        try:
            # Use shield to prevent cancellation from propagating to the close_all_clients method
            await asyncio.shield(manager.close_all_clients())
        except asyncio.CancelledError:
            ... # print("Cleanup was cancelled but resources should still be released")
        except asyncio.TimeoutError:
            ... # print("Timeout during cleanup, some resources may not have been properly released")
        except Exception as e:
            ... # print(f"Error during final cleanup: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
