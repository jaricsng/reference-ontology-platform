#!/usr/bin/env python3
"""CLI for the grounded Q&A agent.

  python ask.py --user nurse_alice "How many free beds are there?"
  python ask.py --user manager_carol "Which wards have the most free beds?"
"""
from __future__ import annotations

import argparse

from agent import ask


def main() -> None:
    p = argparse.ArgumentParser(description="Ask the hospital ontology a question.")
    p.add_argument("question")
    p.add_argument("--user", default="manager_carol",
                   help="identity for security scoping (e.g. nurse_alice, manager_carol)")
    p.add_argument("--show-sparql", action="store_true")
    args = p.parse_args()

    res = ask(args.question, args.user)
    if not res["allowed"]:
        print(res["answer"]); return
    if args.show_sparql:
        print(f"\n--- generated SPARQL (scope: {res['scope']}) ---\n{res['sparql']}\n")
    print(f"Answer ({res['scope']}): {res['answer']}")


if __name__ == "__main__":
    main()
