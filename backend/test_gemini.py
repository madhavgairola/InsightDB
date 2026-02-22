import os
import google.generativeai as genai
import json

# provided key
key = "AQ.Ab8RN6Jp7HRhI-lT-wDttrJlws0l6_UIPmmTw8yxFS8bavhCdw"
genai.configure(api_key=key)

models_to_test = ["gemini-2.0-flash", "gemini-1.5-flash"]

for m_name in models_to_test:
    print(f"Testing model: {m_name}")
    try:
        model = genai.GenerativeModel(m_name)
        response = model.generate_content("Say hello")
        print(f"Success ({m_name}): {response.text}")
        break
    except Exception as e:
        print(f"Error for {m_name}: {e}")
