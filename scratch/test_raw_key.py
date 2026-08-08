import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY")
    print(f"Testing key starting with: {key[:20] if key else 'None'}")
    
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello!"}],
            temperature=0.7
        )
        print("Success! Response from OpenAI:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"OpenAI API call failed: {e}")

if __name__ == "__main__":
    main()
