import asyncio
from typing import Optional, Tuple, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv
import shutil

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self, command, args):
        # Initialize session and client objects
        
        if command == "python":
            self.command = "python"
        elif command =="npx":
            self.command = shutil.which("npx")
        else:
            raise ValueError("Invalid command: must be 'python' or 'npx'")

        self.args = args
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.stdio = None
        self.write = None

    async def connect_to_server(self) -> None:
        """Connect to an MCP server
        """
        # Create a new exit stack for each connection
        self.exit_stack = AsyncExitStack()
        
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=None
        )

        # Use the same task for all async context entries
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        self.tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        


    async def call_tool(self, tool_name: str, input: dict) -> dict:
        """Call an MCP tool by name with input parameters.
        
        Args:
            tool_name: Name of the tool to call
            input: Input parameters for the tool
            
        Returns:
            Output of the tool
        """
        result = ""
        if not self.session:
            raise Exception("Not connected to an MCP server")
        try:
            
            
            print("inside", tool_name, input)
            response = await self.session.call_tool(tool_name, input)
            print(f"[Calling {tool_name} with args {input}]")
            for content in response.content:
                if content.type == "text":
                    result+=content.text
                else:
                    result+=content
    
            return result
        except Exception as e:
            print(f"Error calling tool '{tool_name}': {str(e)}")
            return {"error": str(e)}
    
   
    async def close(self) -> None:
        """Close all connections and clean up resources"""
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except asyncio.CancelledError:
                # Handle cancellation gracefully
                print("Connection closing was cancelled, continuing cleanup")
            except Exception as e:
                print(f"Error during connection cleanup: {str(e)}")
            finally:
                # Ensure resources are cleared even if there was an error
                self.exit_stack = None
                self.session = None
                self.stdio = None
                self.write = None


async def main():
    """Main function to demonstrate MCP client usage"""
    client = MCPClient(command ="npx", args=["@modelcontextprotocol/server-filesystem", "C:/Code", "N:/"])
    try:
        await client.connect_to_server()
        # Add your application logic here
        # For example, wait for user input or process some data
        await asyncio.sleep(1)  # Just a placeholder
        # Access tools if needed
       
        result = await client.call_tool("list_directory", {"path": "C:/Code"})
        print(result)
    except Exception as e:
        print(e)
               
    finally:
        # Ensure resources are properly cleaned up
        await client.close()
  
if __name__ == "__main__":
    asyncio.run(main())
