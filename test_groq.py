from dotenv import load_dotenv
from groq import Groq
import os

# Load .env
load_dotenv()

# Get API key
api_key = os.getenv("GROQ_API_KEY")

# Check whether key exists
if not api_key:
    print("❌ GROQ_API_KEY was not found")
    exit()

print("✅ GROQ_API_KEY found")
print("Key starts with:", api_key[:8] + "********")

# Create Groq client
client = Groq(api_key=api_key)

# Send test request
response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Say hello in one short sentence."
        }
    ],
)

print("\n✅ GROQ API IS WORKING!")
print("Groq response:")
print(response.choices[0].message.content)