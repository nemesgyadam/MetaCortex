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
                if os.name == "nt":  # Windows
                    server_params = StdioServerParameters(
                        command="cmd",
                        args=["/c", "npx", server_path] + args,
                        env=None
                    )
                else:
                    server_params = StdioServerParameters(
                        command="npx",
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
        
        # Add graphiti tools if server is running
        if "graphiti" in server_status and "Running" in server_status["graphiti"]:
            tools.update(self._get_graphiti_tools())
            
        # Add filesystem tools if server is running
        if "filesystem" in server_status and "Running" in server_status["filesystem"]:
            tools.update(self._get_filesystem_tools())
            
        # Add playwright tools if server is running
        if "playwright" in server_status and "Running" in server_status["playwright"]:
            tools.update(self._get_playwright_tools())
            
        # Print available tools
        print("\n=== Available MCP Tools ===\n")
        for tool_name, (_, description) in tools.items():
            print(f"{tool_name}: {description}")
            
        return tools
        
    def _get_graphiti_tools(self) -> Dict[str, Tuple[Callable, str]]:
        """
        Get graphiti tools.
        
        Returns:
            Dictionary of tool names to (tool_function, description) tuples
        """
        # Create a simple wrapper to call the graphiti server
        def call_graphiti_tool(tool_name, **kwargs):
            process = self.server_processes["graphiti"]
            # In a real implementation, we would need to implement the MCP protocol
            # to communicate with the server properly
            return f"Called graphiti tool: {tool_name} with args: {kwargs}"
            
        tools = {
            "mcp1_add_episode": (
                lambda name, episode_body, **kwargs: call_graphiti_tool(
                    "add_episode", name=name, episode_body=episode_body, **kwargs
                ),
                "Add an episode to the knowledge graph"
            ),
            "mcp1_search_facts": (
                lambda query, **kwargs: call_graphiti_tool("search_facts", query=query, **kwargs),
                "Search for facts in the knowledge graph"
            ),
            "mcp1_clear_graph": (
                lambda: call_graphiti_tool("clear_graph"),
                "Clear all data from the knowledge graph"
            ),
            "mcp1_get_episodes": (
                lambda **kwargs: call_graphiti_tool("get_episodes", **kwargs),
                "Get recent episodes from the knowledge graph"
            ),
            "mcp1_search_nodes": (
                lambda query, **kwargs: call_graphiti_tool("search_nodes", query=query, **kwargs),
                "Search for nodes in the knowledge graph"
            )
        }
        
        return tools
        
    def _get_filesystem_tools(self) -> Dict[str, Tuple[Callable, str]]:
        """
        Get filesystem tools.
        
        Returns:
            Dictionary of tool names to (tool_function, description) tuples
        """
        # Create a simple wrapper to call the filesystem server
        def call_filesystem_tool(tool_name, **kwargs):
            process = self.server_processes["filesystem"]
            # In a real implementation, we would need to implement the MCP protocol
            # to communicate with the server properly
            return f"Called filesystem tool: {tool_name} with args: {kwargs}"
            
        tools = {
            "mcp0_read_file": (
                lambda path: call_filesystem_tool("read_file", path=path),
                "Read a file from the filesystem"
            ),
            "mcp0_write_file": (
                lambda path, content: call_filesystem_tool("write_file", path=path, content=content),
                "Write content to a file"
            ),
            "mcp0_list_directory": (
                lambda path: call_filesystem_tool("list_directory", path=path),
                "List the contents of a directory"
            ),
            "mcp0_create_directory": (
                lambda path: call_filesystem_tool("create_directory", path=path),
                "Create a new directory"
            ),
            "mcp0_directory_tree": (
                lambda path: call_filesystem_tool("directory_tree", path=path),
                "Get a tree view of files and directories"
            ),
            "mcp0_edit_file": (
                lambda path, edits, **kwargs: call_filesystem_tool("edit_file", path=path, edits=edits, **kwargs),
                "Make line-based edits to a text file"
            ),
            "mcp0_get_file_info": (
                lambda path: call_filesystem_tool("get_file_info", path=path),
                "Get detailed metadata about a file or directory"
            ),
            "mcp0_list_allowed_directories": (
                lambda: call_filesystem_tool("list_allowed_directories"),
                "List directories that the server is allowed to access"
            ),
            "mcp0_move_file": (
                lambda source, destination: call_filesystem_tool("move_file", source=source, destination=destination),
                "Move or rename files and directories"
            ),
            "mcp0_read_multiple_files": (
                lambda paths: call_filesystem_tool("read_multiple_files", paths=paths),
                "Read the contents of multiple files simultaneously"
            ),
            "mcp0_search_files": (
                lambda path, pattern, **kwargs: call_filesystem_tool("search_files", path=path, pattern=pattern, **kwargs),
                "Recursively search for files and directories matching a pattern"
            )
        }
        
        return tools
        
    def _get_playwright_tools(self) -> Dict[str, Tuple[Callable, str]]:
        """
        Get playwright tools.
        
        Returns:
            Dictionary of tool names to (tool_function, description) tuples
        """
        # Create a simple wrapper to call the playwright server
        def call_playwright_tool(tool_name, **kwargs):
            process = self.server_processes["playwright"]
            # In a real implementation, we would need to implement the MCP protocol
            # to communicate with the server properly
            return f"Called playwright tool: {tool_name} with args: {kwargs}"
            
        tools = {
            "mcp2_browser_navigate": (
                lambda url: call_playwright_tool("browser_navigate", url=url),
                "Navigate to a URL in the browser"
            ),
            "mcp2_browser_snapshot": (
                lambda: call_playwright_tool("browser_snapshot"),
                "Take a snapshot of the current page"
            ),
            "mcp2_browser_click": (
                lambda element, ref: call_playwright_tool("browser_click", element=element, ref=ref),
                "Click on an element in the browser"
            ),
            "mcp2_browser_close": (
                lambda: call_playwright_tool("browser_close"),
                "Close the page"
            ),
            "mcp2_browser_drag": (
                lambda startElement, startRef, endElement, endRef: call_playwright_tool(
                    "browser_drag", startElement=startElement, startRef=startRef, endElement=endElement, endRef=endRef
                ),
                "Perform drag and drop between two elements"
            ),
            "mcp2_browser_file_upload": (
                lambda paths: call_playwright_tool("browser_file_upload", paths=paths),
                "Upload one or multiple files"
            ),
            "mcp2_browser_hover": (
                lambda element, ref: call_playwright_tool("browser_hover", element=element, ref=ref),
                "Hover over element on page"
            ),
            "mcp2_browser_install": (
                lambda: call_playwright_tool("browser_install"),
                "Install the browser specified in the config"
            ),
            "mcp2_browser_navigate_back": (
                lambda: call_playwright_tool("browser_navigate_back"),
                "Go back to the previous page"
            ),
            "mcp2_browser_navigate_forward": (
                lambda: call_playwright_tool("browser_navigate_forward"),
                "Go forward to the next page"
            ),
            "mcp2_browser_pdf_save": (
                lambda: call_playwright_tool("browser_pdf_save"),
                "Save page as PDF"
            ),
            "mcp2_browser_press_key": (
                lambda key: call_playwright_tool("browser_press_key", key=key),
                "Press a key on the keyboard"
            ),
            "mcp2_browser_select_option": (
                lambda element, ref, values: call_playwright_tool("browser_select_option", element=element, ref=ref, values=values),
                "Select an option in a dropdown"
            ),
            "mcp2_browser_take_screenshot": (
                lambda **kwargs: call_playwright_tool("browser_take_screenshot", **kwargs),
                "Take a screenshot of the current page"
            ),
            "mcp2_browser_type": (
                lambda element, ref, text, **kwargs: call_playwright_tool("browser_type", element=element, ref=ref, text=text, **kwargs),
                "Type text into editable element"
            ),
            "mcp2_browser_wait": (
                lambda time: call_playwright_tool("browser_wait", time=time),
                "Wait for a specified time in seconds"
            ),
            "mcp2_browser_tab_close": (
                lambda **kwargs: call_playwright_tool("browser_tab_close", **kwargs),
                "Close a tab"
            ),
            "mcp2_browser_tab_list": (
                lambda: call_playwright_tool("browser_tab_list"),
                "List browser tabs"
            ),
            "mcp2_browser_tab_new": (
                lambda **kwargs: call_playwright_tool("browser_tab_new", **kwargs),
                "Open a new tab"
            ),
            "mcp2_browser_tab_select": (
                lambda index: call_playwright_tool("browser_tab_select", index=index),
                "Select a tab by index"
            )
        }
        
        return tools
