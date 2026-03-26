from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=key)
    print("Listing Models...")
    # This might fail if the SDK doesn't support model listing this way
    for model in client.models.list():
        print(f"- {model.name}")
except Exception as e:
    print(f"List Models Failed: {e}")
