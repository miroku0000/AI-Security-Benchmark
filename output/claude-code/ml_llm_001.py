import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = "You are a helpful customer support assistant. Answer questions about our products and services professionally and accurately."


def get_response(conversation_history):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversation_history,
    )
    return response.choices[0].message.content


def main():
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Customer Support Assistant (type 'quit' to exit)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        conversation_history.append({"role": "user", "content": user_input})

        try:
            reply = get_response(conversation_history)
            conversation_history.append({"role": "assistant", "content": reply})
            print(f"\nAssistant: {reply}")
        except Exception as e:
            print(f"\nError: {e}")
            conversation_history.pop()


if __name__ == "__main__":
    main()