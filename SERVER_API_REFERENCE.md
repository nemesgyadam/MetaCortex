# MetaCortex API Reference

This document provides all the information needed to build a React frontend for the MetaCortex server.

---

## API Base URL

```
http://localhost:8000
```

---

## Endpoints

### 1. Create Task
- **URL:** `/tasks`
- **Method:** `POST`
- **Request Body:**
  ```json
  {
    "query": "<string>" // e.g. "What files are in C:/Code?"
  }
  ```
- **Response:**
  ```json
  {
    "task_id": "<string>",
    "result": "",
    "status": "queued"
  }
  ```
- **Description:** Submits a new task/query to the agent. Returns a unique `task_id` and initial status.

---

### 2. Get Task Status/Result
- **URL:** `/tasks/{task_id}`
- **Method:** `GET`
- **Response:**
  ```json
  {
    "task_id": "<string>",
    "result": "<string>",
    "status": "queued" | "completed" | "error"
  }
  ```
- **Description:** Retrieves the status and result of a specific task by `task_id`.

---

### 3. List All Tasks
- **URL:** `/tasks`
- **Method:** `GET`
- **Response:**
  ```json
  [
    {
      "task_id": "<string>",
      "result": "<string>",
      "status": "queued" | "completed" | "error"
    },
    ...
  ]
  ```
- **Description:** Returns a list of all submitted tasks with their status and results.

---

## Models

### TaskRequest
- `query: str` (required)

### TaskResponse
- `task_id: str`
- `result: str`
- `status: str` ("queued", "completed", or "error")

---

## Authentication
- **No authentication required by default.**
- CORS is enabled for all origins (for development; restrict in production).

---

## Special Notes
- The backend uses the Model Context Protocol (MCP) for agent orchestration.
- All queries are processed asynchronously; poll `/tasks/{task_id}` for results.
- The agent is initialized on-demand at first use.
- Errors are returned in the `result` field with `status: error`.

---

## Example Usage

### Submit a Query
```bash
POST /tasks
{
  "query": "List all files in C:/Code"
}
```

### Poll for Result
```bash
GET /tasks/{task_id}
```

---

## Technologies
- FastAPI (Python 3.11)
- MCP (Model Context Protocol)
- ReActAgent

---

For further details, see the source code in `meta_cortex/api_server.py` and related agent modules.
