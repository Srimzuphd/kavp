"""KAVP command-line interface."""
import sys
import argparse
import kavp


def main():
    parser = argparse.ArgumentParser(
        prog="kavp",
        description="KAVP — Knowledge-Based Policy-Aware Federated AI Framework"
    )
    parser.add_argument("--version", action="version", version=f"kavp {kavp.__version__}")
    parser.add_argument("--info", action="store_true", help="Show KAVP environment info")
    args = parser.parse_args()

    if args.info:
        print(f"KAVP version: {kavp.__version__}")
        print("Core modules: policy_ingestion, parser, graph_builder, constraint_engine, orchestrator, audit_logger")
        print("Extensions: gdpr, metrics[ml], viz")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
