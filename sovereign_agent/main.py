import argparse
from sovereign_agent.agent import SovereignAgent

def main():
    parser = argparse.ArgumentParser(description="Sovereign Agent MVP")
    parser.add_argument("workspace", type=str, nargs="?", default="./agent_workspace",
                        help="Path to project workspace directory")
    args = parser.parse_args()
    agent = SovereignAgent(workspace_path=args.workspace)
    agent.start_session()

if __name__ == "__main__":
    main()
