import argparse
import json
import os

import httpx

BASE_URL = "http://127.0.0.1:8000"

HELP = """
Commands:
  agents              — list registered agents and their status
  results <agent_id>  — show task results for an agent
  help                — show this message
  exit                — quit
"""


def make_client(api_key: str) -> httpx.Client:
    """Create an HTTP client configured with the operator API key."""
    return httpx.Client(
        base_url=BASE_URL,
        headers={"x-operator-key": api_key},
        timeout=10.0,
    )


def print_agents(client: httpx.Client) -> None:
    """Fetch and print all registered agents."""
    resp = client.get("/api/v1/operator/agents")
    resp.raise_for_status()
    agents = resp.json()
    if not agents:
        print("No agents registered.")
        return
    print(f"{'ID':<45} {'STATUS':<12} {'PLATFORM':<10} {'LAST SEEN'}")
    print("-" * 90)
    for a in agents:
        print(f"{a['agent_id']:<45} {a['status']:<12} {a['platform']:<10} {a['last_seen_at']}")


def print_results(client: httpx.Client, agent_id: str) -> None:
    """Fetch and print tasks and results for a given agent."""
    resp = client.get(f"/api/v1/operator/agents/{agent_id}/results")
    resp.raise_for_status()
    tasks = resp.json()
    if not tasks:
        print("No tasks for this agent.")
        return
    for t in tasks:
        print(f"\n[{t['task_id']}]  type={t['task_type']}  status={t['status']}")
        if t.get("result"):
            print("  result:", json.dumps(t["result"], indent=4))
        if t.get("error"):
            print("  error:", t["error"])


def run_cli(api_key: str) -> None:
    """Run the interactive C2 operator command loop."""
    with make_client(api_key) as client:
        print("C2 Operator CLI  (type 'help' for commands)")
        while True:
            try:
                line = input("c2> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()

            try:
                if cmd == "agents":
                    print_agents(client)
                elif cmd == "results" and len(parts) == 2:
                    print_results(client, parts[1])
                elif cmd in ("help", "?"):
                    print(HELP)
                elif cmd in ("exit", "quit"):
                    break
                else:
                    print("Unknown command. Type 'help'.")
            except httpx.HTTPStatusError as exc:
                print(f"Server error {exc.response.status_code}: {exc.response.text}")
            except httpx.RequestError as exc:
                print(f"Could not reach server: {exc}")


def main() -> None:
    """Parse CLI arguments and launch the interactive operator shell."""
    parser = argparse.ArgumentParser(description="C2 Operator CLI")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--key", default=os.getenv("C2_OPERATOR_KEY", "dev-operator-key"))
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.server.rstrip("/")
    run_cli(args.key)


if __name__ == "__main__":
    main()
