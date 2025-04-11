# ReAct Agent with OpenRouter and MCP Servers

A Python implementation of the ReAct (Reasoning, Action, Observation) pattern for LLMs using OpenRouter models and MCP (Model Context Protocol) servers. This agent can perform reasoning and take actions to solve tasks using local MCP servers.

## Setup

1. Install dependencies:
   ```
   pip install httpx python-dotenv
   ```

2. Create a `.env` file with your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```
   You can get an API key at [https://openrouter.ai/keys](https://openrouter.ai/keys)

3. Ensure your `mcp_config.json` file is properly configured with the MCP servers you want to use. The default configuration includes:
   - `graphiti` - Knowledge graph server
   - `playwright` - Web browsing server
   - `filesystem` - File system access server

4. Run the demo:
   ```
   python demo.py
   ```

## Components

- `react_agent.py` - Core implementation of the ReAct pattern
- `mcp_client.py` - Client for interacting with MCP servers
- `mcp_tools.py` - Adapter for MCP server tools to be used with the ReAct agent
- `demo.py` - Demo script to showcase the agent in action
- `mcp_config.json` - Configuration file for MCP servers

## Available Models

The demo supports various models through OpenRouter:
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku
- Gemini Pro
- GPT-4 Turbo
- GPT-3.5 Turbo
- Llama 3 70B

## Available MCP Tools

The agent comes with several MCP-based tools:

### Filesystem Tools
- `list_directory` - List the contents of a directory
- `read_file` - Read the contents of a file
- `write_file` - Write content to a file

### Graphiti Tools
- `search_knowledge` - Search the knowledge graph
- `add_knowledge` - Add information to the knowledge graph

### Playwright Tools
- `browse` - Browse a website and get its content
- `screenshot` - Take a screenshot of the current page

## Extending

You can add your own MCP tools by:
1. Adding new methods to the `MCPTools` class in `mcp_tools.py`
2. Adding them to the `get_available_tools()` method

You can also add new MCP servers by updating the `mcp_config.json` file.

## Based On

This implementation is based on Simon Willison's article: [A simple Python implementation of the ReAct pattern for LLMs](https://til.simonwillison.net/llms/python-react-pattern)
