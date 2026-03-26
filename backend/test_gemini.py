from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")

print(f"Testing Gemini Key: {key[:10]}...")
try:
    client = genai.Client(api_key=key)
    # Use the model the user mentioned might be 2.0 (interpreted from 2.5)
    # We will try the most common names
    for model_name in ['gemini-2.0-flash-exp', 'gemini-1.5-flash']:
        print(f"Trying model: {model_name}...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Hello, identify yourself."
            )
            print(f"SUCCESS with {model_name}!")
            print(f"Response: {response.text}")
            break
        except Exception as inner:
            print(f"Failed with {model_name}: {inner}")
except Exception as e:
    print(f"Initialization Failed: {e}")
