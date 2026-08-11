"""
Manual smoke test for the Anthropic account/API key set up in Week 1 issue #3.

Not part of the Lambda or the automated test suite — run by hand to confirm
ANTHROPIC_API_KEY is valid and billing is wired up correctly.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python backend/mealplan/test_claude_call.py
"""
import os
import sys

import anthropic


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set in the environment.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": "Say hello and confirm which Claude model you are.",
            }
        ],
    )

    for block in response.content:
        if block.type == "text":
            print(block.text)


if __name__ == "__main__":
    main()