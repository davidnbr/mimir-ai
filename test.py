#!/usr/bin/env python3
"""Test Gemini API directly using new google-genai package."""
import os
from dotenv import load_dotenv

load_dotenv()

from google import genai

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key (first 10 chars): {api_key[:10]}...")

client = genai.Client(api_key=api_key)

# List available models
print("\nAvailable models:")
for model in client.models.list():
    print(f"  - {model.name}")

# Test with gemini-2.5-flash
print("\nTesting gemini-2.5-flash...")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say 'JARVIS online' in a British butler style. Keep it short.",
)
print(f"Response: {response.text}")
