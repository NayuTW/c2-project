from dataclasses import dataclass


# Only placeholder types for milestone 1
@dataclass
class AgentRecord:
    agent_id: str
    session_token_hash: str
    platform: str
    architecture: str