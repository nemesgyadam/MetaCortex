"""
MCP client implementation for the ReAct agent.
Manages MCP servers defined in the configuration file.
"""
import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from mcp import StdioServerParameters
import shutil

class MCPClient:
    """
    Manages MCP servers defined in the configuration file.
    Provides tools for the ReAct agent to use.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the MCP client.
        
        Args:
            config_path: Path to the MCP configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.server_processes: Dict[str, subprocess.Popen] = {}
        self.server_status: Dict[str, str] = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load the MCP configuration file.
        
        Returns:
            The configuration as a dictionary
        """
        print(f"Loading MCP config from: {self.config_path}")
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
            return {}
            
    def get_available_servers(self) -> List[str]:
        """
        Get the list of available servers from the configuration.
        
        Returns:
            List of server names
        """
        servers = list(self.config.get("mcpServers", {}).keys())
        print(f"Found servers in config: {', '.join(servers)}")
        return servers
        
    def start_all_servers(self) -> Dict[str, str]:
        """
        Start all MCP servers defined in the configuration.
        
        Returns:
            Dictionary of server names to their status
        """
        servers = self.get_available_servers()
        print(f"Available servers: {set(servers)}")
        
        for server_name in servers:
            self.start_server(server_name)
            
        return self.get_server_status()
        
    def start_server(self, server_name: str) -> bool:
        """
        Start an MCP server by name.
        
        Args:
            server_name: Name of the server to start
            
        Returns:
            True if server started successfully, False otherwise
        """
        if server_name not in self.config.get("mcpServers", {}):
            print(f"Server '{server_name}' not found in configuration")
            self.server_status[server_name] = "Not configured"
            return False
            
        if server_name in self.server_processes and self.server_processes[server_name].poll() is None:
            print(f"Server '{server_name}' is already running")
            self.server_status[server_name] = "Running"
            return True
            
        server_config = self.config["mcpServers"][server_name]
        server_type = server_config.get("type")
        server_path = server_config.get("path")
        args = server_config.get("args", [])
        

        # Use the MCP Python package to start the server
        if server_type == "python":
            command = "python"
        elif server_type == "node":
            command = "node"
        else:
            print(f"Unknown server type: {server_type}")
            self.server_status[server_name] = f"Failed to start: Unknown server type {server_type}"
            return False
            
        print(f"Starting MCP server '{server_name}' with {server_type} server: {server_path}")
        self.server_status[server_name] = "Starting"
        
        try:
            # Create server parameters using the MCP package
            if server_type == "python":
                server_params = StdioServerParameters(
                    command="python",
                    args=[server_path] + args,
                    env=None
                )
            elif server_type == "node":
                # For node packages on Windows, use cmd /c npx to avoid execution policy issues
                # if os.name == "nt":  # Windows
                #     server_params = StdioServerParameters(
                #         command="cmd",
                #         args=["/c", "npx", server_path] + args,
                #         env=None
                #     )
                # else:
                print("---------", args)
                server_params = StdioServerParameters(
                    command=shutil.which("npx"),
                    args=[server_path] + args,
                    env=None
                )
            
            # Start the server process
            process = subprocess.Popen(
                [server_params.command] + server_params.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.server_processes[server_name] = process
            
            # Wait a moment to see if the process exits immediately
            time.sleep(2)
            
            # Check if the process is still running
            if process.poll() is None:
                self.server_status[server_name] = "Running"
                print(f"Started MCP server: {server_name}")
                return True
            else:
                # Process exited, get the error message
                _, stderr = process.communicate()
                self.server_status[server_name] = f"Failed to start: {stderr}"
                print(f"Error starting server '{server_name}': {stderr}")
                return False
                
        except Exception as e:
            print(f"Error starting server '{server_name}': {str(e)}")
            self.server_status[server_name] = f"Failed: {str(e)}"
            return False
            
    def stop_server(self, server_name: str) -> bool:
        """
        Stop an MCP server by name.
        
        Args:
            server_name: Name of the server to stop
            
        Returns:
            True if server stopped successfully, False otherwise
        """
        if server_name not in self.server_processes:
            print(f"Server '{server_name}' is not running")
            return False
            
        process = self.server_processes[server_name]
        
        # Terminate the process
        try:
            process.terminate()
            process.wait(timeout=5)
            del self.server_processes[server_name]
            self.server_status[server_name] = "Stopped"
            return True
        except Exception as e:
            print(f"Error stopping server '{server_name}': {str(e)}")
            try:
                process.kill()
                process.wait(timeout=5)
                del self.server_processes[server_name]
                self.server_status[server_name] = "Killed"
                return True
            except Exception as e2:
                print(f"Error killing server '{server_name}': {str(e2)}")
                self.server_status[server_name] = f"Failed to stop: {str(e2)}"
                return False
                
    def stop_all_servers(self) -> None:
        """
        Stop all running MCP servers.
        """
        for server_name in list(self.server_processes.keys()):
            self.stop_server(server_name)
            
    def get_server_status(self) -> Dict[str, str]:
        """
        Get the status of all MCP servers.
        
        Returns:
            Dictionary of server names to their status
        """
        # Update status for running servers
        for server_name, process in list(self.server_processes.items()):
            if process.poll() is None:
                self.server_status[server_name] = "Running"
            else:
                self.server_status[server_name] = f"Exited with code {process.returncode}"
                
        return self.server_status
        
    def format_status_table(self) -> str:
        """
        Format the server status as a markdown table.
        
        Returns:
            Markdown table of server status
        """
        status = self.get_server_status()
        
        table = "| Server | Status |\n|--------|--------|\n"
        for server, status_text in status.items():
            status_indicator = "[RUNNING]" if "Running" in status_text else "[FAILED]"
            table += f"| {server} | {status_indicator} {status_text} |\n"
            
        return table
        
    def get_tools(self) -> Dict[str, Tuple[Callable, str]]:
        """
        Get all available MCP tools in the format expected by the ReAct agent.
        Only includes tools for servers that are actually running.
        
        Returns:
            Dictionary of tool names to (tool_function, description) tuples
        """
        tools = {}
        server_status = self.get_server_status()
       
            
        return tools
        