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

from mcp_client import MCPClient


class ClientManager:
    """
    Manages multiple MCP clients based on configuration from JSON files.
    Creates and maintains connections to multiple MCP servers.
    """
    
    def __init__(self, config_file_path: Optional[str] = None, verbose: bool = True):
        """
        Initialize the client manager with a configuration file path.
        
        Args:
            config_file_path: Path to the JSON configuration file.
                             If None, defaults to mcp_config.json in the meta_cortex directory.
            verbose: If True, print detailed logs about operations. If False, suppress most logs.
        """
        # Set default config path if none provided
        if config_file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_file_path = os.path.join(base_dir, "mcp_config.json")
        else:
            self.config_file_path = config_file_path
            
        self.verbose = verbose  # Store the verbose flag
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
                if self.verbose:
                    print(f"Configuration file {self.config_file_path} does not exist")
                return {}
                
            with open(self.config_file_path, 'r') as f:
                self.config = json.load(f)
                if self.verbose:
                    print(f"Loaded MCP configuration from {self.config_file_path}")
                return self.config
        except json.JSONDecodeError:
            if self.verbose:
                print(f"Error parsing JSON in {self.config_file_path}")
            return {}
        except Exception as e:
            if self.verbose:
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
        Get all available tools from connected servers.
        
        Returns:
            Dictionary mapping tool names to tuples of (function, description)
        """
        tools = {}
        for server_name, client in self.connected_clients.items():
            if client and hasattr(client, 'get_tools'):
                server_tools = client.get_tools()
                if server_tools:
                    for name, (func, desc) in server_tools.items():
                        full_name = f"{server_name}.{name}"
                        tools[full_name] = (func, desc)
        return tools
    
    def is_connected(self, server_name: str) -> bool:
        """
        Check if a specific server is connected and operational.
        
        Args:
            server_name: Name of the server to check
            
        Returns:
            bool: True if server is connected and operational
        """
        return (
            server_name in self.connected_clients and 
            self.connected_clients[server_name] is not None and
            hasattr(self.connected_clients[server_name], 'is_connected') and 
            self.connected_clients[server_name].is_connected()
        )

    async def create_clients(self) -> Dict[str, MCPClient]:
        """
        Create MCP clients for all servers defined in the configuration.
        
        Returns:
            Dictionary of server names to MCPClient instances
        """
        # Create clients for each server in the config
        for server_name, server_config in self.config.get("mcpServers", {}).items():
            try:
                # Extract command and args from the server config
                command = server_config.get("command")
                args = server_config.get("args", [])
                
                if not command:
                    raise ValueError(f"Missing 'command' in configuration for server {server_name}")
                
                # Create a new client for this server
                client = MCPClient(command=command, args=args)
                self.clients[server_name] = client
                if self.verbose:
                    print(f"Created client for server: {server_name}")
            except Exception as e:
                if self.verbose:
                    print(f"Error creating client for server {server_name}: {str(e)}")
                self.clients[server_name] = None
                
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
            
        # We need to ensure each client connection runs in a fresh task
        # This is crucial for proper asyncio handling, especially in FastAPI context
        connect_tasks = []
        
        for server_name, client in self.clients.items():
            if client is None:
                continue
                
            # Create a task for each connection attempt
            connect_task = asyncio.create_task(self._connect_client(server_name, client))
            connect_tasks.append(connect_task)
        
        # Wait for all connections to complete
        if connect_tasks:
            await asyncio.gather(*connect_tasks, return_exceptions=True)
                
        return self.connected_clients
        
    async def _connect_client(self, server_name: str, client: MCPClient) -> None:
        """
        Connect to a single MCP server with proper error handling.
        
        Args:
            server_name: Name of the server
            client: MCPClient instance to connect
        """
        try:
            # Create a new task for connection to ensure proper asyncio handling
            await client.connect_to_server()
            # Update the connected clients dictionary only if the client is actually connected
            if client.is_connected():
                self.connected_clients[server_name] = client
                if self.verbose:
                    print(f"Connected to server: {server_name}")
            else:
                if self.verbose:
                    print(f"Failed to establish a working connection to server: {server_name}")
        except Exception as e:
            if self.verbose:
                print(f"Error connecting to server {server_name}: {str(e)}")
    
    async def close_all_clients(self) -> None:
        """
        Close all connected clients and clean up resources.
        """
        # Create a list of clients to avoid modifying the dictionary during iteration
        client_items = list(self.clients.items())
        
        # Close each client individually without using tasks
        for server_name, client in client_items:
            if hasattr(client, 'exit_stack') and client.exit_stack is not None:
                try:
                    # Use a simple try-except block instead of tasks
                    await self._close_client(server_name, client)
                except Exception as e:
                    if self.verbose:
                        print(f"Error closing client {server_name}: {str(e)}")
            else:
                if self.verbose:
                    print(f"Client {server_name} has no exit_stack, skipping close")
        
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
            if self.verbose:
                print(f"Closed connection to server: {server_name}")
        except asyncio.CancelledError:
            if self.verbose:
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
            if self.verbose:
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
        if self.verbose:
            print(f"[Client manager calls tool {tool_name} on server {server_name}]")
        # # Make sure we have connected clients
        # if not self.connected_clients:
        #     await self.connect_all_clients()
            
        if server_name not in self.connected_clients:
            raise ValueError(f"Server {server_name} is not connected")
            
        client = self.connected_clients[server_name]
        
        try:
            result = await client.call_tool(tool_name, params)
            return result
        except Exception as e:
            error_msg = f"Error calling tool {tool_name} on server {server_name}: {str(e)}"
            if self.verbose:
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
        # Query free/busy information for a specific calendar and time range
        result = await manager.call_tool("Google Calendar", "google_calendar-query-free-busy-calendars", {
            "calendarId": "primary",
            "timeMin": "2025-04-27T00:00:00Z",
            "timeMax": "2025-04-27T23:59:59Z"
        })
        # Example: Call a tool on the filesystem server if available
        #if "filesystem" in server_names:
        #    result = await manager.call_tool("filesystem", "list_directory", {"path": "C:/Code"})
        #   print(f"Directory listing result: {result}")
        print("#"*100)
        print(result)
        print("#"*100)
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
