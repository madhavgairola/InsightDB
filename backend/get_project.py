import google.auth

try:
    credentials, project_id = google.auth.default()
    print(f"Detected Project ID: {project_id}")
except Exception as e:
    print(f"Error detecting project: {e}")
