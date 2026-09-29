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
