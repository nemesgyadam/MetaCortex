# LiveKit Voice AI

A simple voice assistant built with LiveKit Agents and Python.

## Setup Instructions

### 1. Create a virtual environment using uv

```bash
# Install uv if not already installed
pip install uv

# Create and activate virtual environment
uv venv .venv
.\.venv\Scripts\activate
```

### 2. Install dependencies

```bash
uv pip install -r requirements.txt
```

### 3. Configure environment variables

Edit the `.env` file and add your API keys:
- Deepgram API Key
- OpenAI API Key
- Cartesia API Key
- LiveKit API Key
- LiveKit API Secret
- LiveKit URL

### 4. Run the application

```bash
python main.py
```

## Requirements

- Python 3.11+
- LiveKit server
- API keys for the required AI providers (Deepgram, OpenAI, Cartesia)