"""
Simple test script that uses the filesystem MCP to list files in c:/Code

This implements a simple MCP-like pattern for filesystem operations.
"""
import os
import json
from typing import Dict, Any, List, Optional
import datetime


class FilesystemMCPServer:
    """
    A simple implementation of an MCP server for filesystem operations.
    Follows the Model Context Protocol pattern but uses Python's standard libraries.
    """
    def __init__(self, allowed_directories: List[str]):
        """
        Initialize the filesystem MCP server with allowed directories.
        
        Args:
            allowed_directories: List of directories that the server is allowed to access
        """
        self.allowed_directories = allowed_directories
        print(f"Filesystem MCP Server initialized")
        print(f"Allowed directories: {', '.join(allowed_directories)}")
    
    def _is_path_allowed(self, path: str) -> bool:
        """
        Check if a path is within the allowed directories.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path is allowed, False otherwise
        """
        path = os.path.abspath(path)
        return any(path.startswith(os.path.abspath(allowed_dir)) for allowed_dir in self.allowed_directories)
    
    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """
        List the contents of a directory.
        
        Args:
            path: Path to the directory to list
            
        Returns:
            List of dictionaries containing file/directory information
        """
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access to {path} is not allowed")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path {path} does not exist")
        
        if not os.path.isdir(path):
            raise NotADirectoryError(f"Path {path} is not a directory")
        
        result = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            stats = os.stat(item_path)
            is_dir = os.path.isdir(item_path)
            
            # Format the result similar to how an MCP server would
            result.append({
                "name": item,
                "path": item_path,
                "isDirectory": is_dir,
                "size": stats.st_size,
                "created": datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "accessed": datetime.datetime.fromtimestamp(stats.st_atime).isoformat(),
            })
        
        return result
    
    def directory_tree(self, path: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Get a tree view of a directory.
        
        Args:
            path: Path to the directory to get a tree view of
            max_depth: Maximum depth of the tree
            
        Returns:
            Dictionary containing the tree structure
        """
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access to {path} is not allowed")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path {path} does not exist")
        
        if not os.path.isdir(path):
            raise NotADirectoryError(f"Path {path} is not a directory")
        
        def build_tree(current_path: str, current_depth: int) -> Dict[str, Any]:
            stats = os.stat(current_path)
            name = os.path.basename(current_path) or current_path
            result = {
                "name": name,
                "path": current_path,
                "isDirectory": os.path.isdir(current_path),
                "size": stats.st_size,
                "modified": datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
            }
            
            if os.path.isdir(current_path) and current_depth < max_depth:
                result["children"] = []
                try:
                    for item in os.listdir(current_path):
                        item_path = os.path.join(current_path, item)
                        result["children"].append(build_tree(item_path, current_depth + 1))
                except PermissionError:
                    result["error"] = "Permission denied"
            
            return result
        
        return build_tree(path, 0)


class MCPClient:
    """
    A simple MCP client that communicates with the filesystem MCP server.
    """
    def __init__(self, server: FilesystemMCPServer):
        """
        Initialize the MCP client with a server.
        
        Args:
            server: The MCP server to communicate with
        """
        self.server = server
    
    def call_method(self, method_name: str, **kwargs) -> Any:
        """
        Call a method on the MCP server.
        
        Args:
            method_name: Name of the method to call
            **kwargs: Arguments to pass to the method
            
        Returns:
            Result of the method call
        """
        if not hasattr(self.server, method_name):
            raise AttributeError(f"Method {method_name} not found on server")
        
        method = getattr(self.server, method_name)
        return method(**kwargs)


def main() -> None:
    """
    Main function to test the filesystem MCP functionality.
    Lists files in c:/Code using our simple MCP implementation.
    """
    print("Testing filesystem MCP to list files in c:/Code")
    
    # Create the filesystem MCP server
    server = FilesystemMCPServer(["c:/Code", "N:/"])
    
    # Create the MCP client
    client = MCPClient(server)
    
    try:
        # List files in c:/Code
        print("\nListing files in c:/Code:")
        files = client.call_method("list_directory", path="c:/Code")
        
        # Display the results
        if files:
            for item in files:
                item_type = "Directory" if item.get("isDirectory") else "File"
                name = item.get("name", "Unknown")
                size = item.get("size", 0)
                modified = item.get("modified", "Unknown")
                print(f"{item_type}: {name} ({size} bytes, modified: {modified})")
        
        # Get directory tree
        print("\nGetting directory tree for c:/Code (limited to depth 1):")
        tree = client.call_method("directory_tree", path="c:/Code", max_depth=1)
        
        # Print the root of the tree
        print(f"Root: {tree['name']} ({tree['size']} bytes)")
        
        # Print the first level of children
        if "children" in tree:
            print("Children:")
            for child in tree["children"]:
                child_type = "Directory" if child.get("isDirectory") else "File"
                name = child.get("name", "Unknown")
                size = child.get("size", 0)
                print(f"  {child_type}: {name} ({size} bytes)")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
