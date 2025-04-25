# MetaCortex Universal Multiagent AI Framework

MetaCortex is a modular, extensible Python framework for building multiagent AI assistants using the Model Context Protocol (MCP) and the latest open-source and commercial LLMs. The framework provides:

- **Universal agent orchestration** (ReAct, tool-use, context sharing)
- **Seamless integration with MCP servers** (knowledge graph, web browsing, filesystem, etc.)
- **Voice AI support** (LiveKit integration)
- **Modern, modular codebase** with type hints and PEP8 compliance

## Features
- **ReAct agent** with OpenRouter LLM support
- **MCP tools**: knowledge graph, web, filesystem, and more
- **Voice AI**: real-time voice assistant via LiveKit
- **Easy extensibility**: add new MCP tools or agents

## Quickstart

### 1. Clone and set up
```bash
git clone <repo_url>
cd MetaCortex_v1
```

### 2. Create and activate virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r livekit-voice-ai/requirements.txt
pip install httpx python-dotenv
```

### 4. Configure environment variables
- Edit `.env` files in `meta_cortex` and `livekit-voice-ai` as needed (API keys for OpenRouter, Deepgram, LiveKit, etc.)

### 5. Run
- **Text agent demo:**
  ```bash
  cd meta_cortex
  python demo.py
  ```
- **Voice AI:**
  ```bash
  cd livekit-voice-ai
  python main.py
  ```

## Directory Structure
- `meta_cortex/` — Core multiagent framework (ReAct agent, MCP client, config)
- `livekit-voice-ai/` — Real-time voice assistant (LiveKit, Deepgram, OpenAI, Cartesia integration)
- `prompts/` — Agent/task prompt templates

## Technologies
- Python 3.11+
- Model Context Protocol (MCP)
- OpenRouter (LLM API)
- LiveKit (voice streaming)
- Deepgram, OpenAI, Cartesia (AI providers)

## Extending
- Add new MCP servers in `meta_cortex/mcp_config.json`
- Add tools in `meta_cortex/mcp_tools.py`
- Add agents or prompts in `prompts/`

## License
MIT

---
For detailed component usage, see the `README.md` files in each submodule (`meta_cortex/`, `livekit-voice-ai/`).
