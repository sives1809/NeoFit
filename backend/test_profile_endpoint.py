from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user, get_db

# Override dependencies for testing
mock_user = {
    "user_id": "1eed0d2f-895b-4f9a-856a-9e059809eb6c", # Existing user in DB
    "email": "sives@example.com",
    "role": "authenticated",
}

client = TestClient(app)

# We use the real DB but mock the auth to return the existing user's ID
app.dependency_overrides[get_current_user] = lambda: mock_user

print("--- GET /api/v1/profile ---")
resp = client.get("/api/v1/profile")
print("Status:", resp.status_code)
print("Data:", resp.json())

print("--- PUT /api/v1/profile ---")
update_payload = {
    "full_name": "Sives Sundar Manna New",
    "age": 23,
    "sex": "male",
    "height_cm": 171.45,
    "weight_kg": 78.0,
    "activity_level": "active",
    "fitness_goal": "lose_fat",
    "diet_pref": "vegetarian"
}
resp = client.put("/api/v1/profile", json=update_payload)
print("Status:", resp.status_code)
print("Data:", resp.json())

print("--- GET /api/v1/profile after update ---")
resp = client.get("/api/v1/profile")
print("Status:", resp.status_code)
print("Data:", resp.json())
