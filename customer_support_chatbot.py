import os
import sys

from openai import OpenAI

SYSTEM_INSTRUCTIONS = (
    "You are a professional customer support assistant. "
    "Be helpful, accurate, empathetic, and concise. "
    "If you do not know something, say so and offer to escalate or gather more details."
)


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY in your environment.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    while True:
        try:
            user_message = input("Customer: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_message:
            continue

        if user_message.lower() in {"quit", "exit", "q"}:
            break

        combined_input = f"{SYSTEM_INSTRUCTIONS}\n\n{user_message}"

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": combined_input}],
        )

        reply = response.choices[0].message.content or ""
        print(reply)


if __name__ == "__main__":
    main()
