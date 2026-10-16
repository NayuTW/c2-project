## Objective:
Create and evaluate a lightweight authenticated Python task-orchestration server and benign agent in an isolated virtual network.

## Target Features:
- What the server will do:
    - Register agents
    - Assign each agent an ID
    - Track last-seen time
    - Queue allowlisted tasks
    - Return tasks when an agent polls
    - Receive task results
    - Store agents, tasks, and results in SQLite
    - Authenticated requests
    - Validate all request data
    - Record audit events
- What the agent will do:
    - Register with the server
    - Poll periodically
    - Accept only predefined tasks
    - Execite tasks locally
    - Submit structured results
    - Retry safely after temporary failures
    - Stop cleanly

## Safe task types
- Only safe task types can be used such as:
    - `get_host_metadata`
    - `echo`
    - `sleep`
    - `list_test_directory`
    - `read_test_file`
- Restrict file access to a dedicated directory such as `/tmp/c2-test`

## How to use:
At its current stage in development, you can use uv in two separate terminals to start both the server and the agent. APIs can be used either by interacting with the '/docs' web page or with curl

### Starting the Server:
- To start the server you can use the following command in the project root directory:
  - `uv run uvicorn c2.server.app:app --reload`
- Once the server has started the APIs can be tested by navigating to '127.0.0.1:8000/docs' and interacting with the web page.

### Starting the Agent:
- To start the agent you can use the following command in the project root directory:
  - `uv run python -m c2.agent.main`
  - Note: You can also use the --poll-once flag to create and register an agent that will poll one time then stop running.
- Once the agent has started it will provide the agent ID 'agent-1234-abc...' which is needed to create tasks.

### Creating Tasks:
- To create a task you can either use the web page located at '127.0.0.1:8000/docs' or you may use curl.
  - To use curl to create a task you may use a POST request like the following:
  ```python
  curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/tasks' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "agent_id": "agent-1234-abc...",
  "task_type": "get_host_metadata",
  "parameters": {}
  }'
```
