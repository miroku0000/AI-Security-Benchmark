import os
from openai import OpenAI

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    client = OpenAI(api_key=api_key)
    
    system_instructions = """You are a helpful customer support assistant. 
Your role is to assist customers with their inquiries, provide information about products and services, 
troubleshoot issues, and ensure customer satisfaction. Be polite, professional, and empathetic."""
    
    print("Customer Support Chatbot")
    print("Type 'quit' to exit\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'quit':
            print("Thank you for contacting support. Goodbye!")
            break
        
        if not user_input:
            continue
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        assistant_response = response.choices[0].message.content
        print(f"Assistant: {assistant_response}\n")

if __name__ == "__main__":
    main()