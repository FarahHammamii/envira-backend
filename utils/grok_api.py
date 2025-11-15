import requests
import os

GROK_API_KEY = os.getenv("GROK_API_KEY")

def analyze_sentiment(text):
    url = "https://api.grok.ai/sentiment"
    headers = {"Authorization": f"Bearer {GROK_API_KEY}"}
    response = requests.post(url, json={"text": text}, headers=headers)
    if response.status_code == 200:
        return response.json()
    return {"error": "Failed to analyze sentiment"}
