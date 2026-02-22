import vertexai
from vertexai.generative_models import GenerativeModel
import os

# The user provided this: AQ.Ab8RN6Jp7HRhI-lT-wDttrJlws0l6_UIPmmTw8yxFS8bavhCdw
# If this is a token, we might need to set it in the environment or use a specific auth method.
# But let's try to see if we can init vertexai with a dummy project if it's already auth-ed.

project = "hackfest-2.0" # Dummy or actual? User didn't specify.
location = "us-central1"

try:
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-1.5-flash") # 2.5 might not be here yet
    response = model.generate_content("Say hello")
    print(f"Success: {response.text}")
except Exception as e:
    print(f"Vertex AI Init failed: {e}")
