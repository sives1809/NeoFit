import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user, get_db
from tests.test_cv import make_landmarks

# Override dependencies for integration testing
mock_user = {
    "user_id": "00000000-0000-0000-0000-000000000000",
    "email": "test-integration@example.com",
    "role": "authenticated",
}

global_inserted_sessions = []

class MockQuery:
    def __init__(self, table_name, data=None):
        self.table_name = table_name
        self.data = data

    def insert(self, row):
        if self.table_name == "sessions":
            if "captured_at" not in row:
                from datetime import datetime, timezone
                row["captured_at"] = datetime.now(timezone.utc).isoformat()
            global_inserted_sessions.append(row)
        return MockQuery(self.table_name, [row])

    def select(self, *args):
        return self

    def eq(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        class Result:
            def __init__(self, data):
                self.data = data
        if self.table_name == "profiles":
            return Result({"fitness_goal": "muscle_gain"})
        return Result(self.data if self.data is not None else list(reversed(global_inserted_sessions)))

class MockDB:
    def table(self, name):
        return MockQuery(name)

@pytest.fixture(autouse=True)
def override_db():
    global_inserted_sessions.clear()
    app.dependency_overrides[get_db] = lambda: MockDB()
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

def test_full_workflow_integration():
    client = TestClient(app)

    # Step 1: Reset the measurement state
    resp = client.post("/api/v1/measure/reset")
    assert resp.status_code == 200
    assert resp.json().get("status") == "reset"

    # Step 2: Test LEFT orientation validation rejection
    # We send right-facing profile during left_side mode
    lms_right = make_landmarks(side_mode=True, facing="right")
    serialized_lms_right = [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in lms_right]
    
    resp = client.post("/api/v1/measure/frame", json={
        "height_cm": 175,
        "landmarks": serialized_lms_right,
        "video_width": 640,
        "video_height": 480,
        "mode": "left_side"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["validation"]["ok"] is False
    assert "Turn to your right (showing LEFT profile)" in data["validation"]["reason"]

    # Step 3: Test RIGHT orientation validation rejection
    # We send left-facing profile during right_side mode
    lms_left = make_landmarks(side_mode=True, facing="left")
    serialized_lms_left = [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in lms_left]
    
    resp = client.post("/api/v1/measure/frame", json={
        "height_cm": 175,
        "landmarks": serialized_lms_left,
        "video_width": 640,
        "video_height": 480,
        "mode": "right_side"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["validation"]["ok"] is False
    assert "Turn to your left (showing RIGHT profile)" in data["validation"]["reason"]

    # Step 4: Run the actual FRONT capture workflow
    # Send consecutive front frames to calibrate stability
    lms_front = make_landmarks(side_mode=False)
    serialized_lms_front = [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in lms_front]
    
    front_captured_data = None
    for i in range(12):
        resp = client.post("/api/v1/measure/frame", json={
            "height_cm": 175,
            "landmarks": serialized_lms_front,
            "video_width": 640,
            "video_height": 480,
            "mode": "front"
        })
        assert resp.status_code == 200
        data = resp.json()
        if data.get("ready_to_capture"):
            front_captured_data = data
            break
            
    assert front_captured_data is not None, "Front capture did not trigger stability"
    assert front_captured_data["validation"]["ok"] is True

    # Step 5: Run LEFT SIDE capture workflow
    left_captured_data = None
    for i in range(12):
        resp = client.post("/api/v1/measure/frame", json={
            "height_cm": 175,
            "landmarks": serialized_lms_left,
            "video_width": 640,
            "video_height": 480,
            "mode": "left_side"
        })
        assert resp.status_code == 200
        data = resp.json()
        if data.get("ready_to_capture"):
            left_captured_data = data
            break
            
    assert left_captured_data is not None, "Left side capture did not trigger stability"
    assert left_captured_data["validation"]["ok"] is True

    # Step 6: Run RIGHT SIDE capture workflow
    right_captured_data = None
    for i in range(12):
        resp = client.post("/api/v1/measure/frame", json={
            "height_cm": 175,
            "landmarks": serialized_lms_right,
            "video_width": 640,
            "video_height": 480,
            "mode": "right_side"
        })
        assert resp.status_code == 200
        data = resp.json()
        if data.get("ready_to_capture"):
            right_captured_data = data
            break
            
    assert right_captured_data is not None, "Right side capture did not trigger stability"
    assert right_captured_data["validation"]["ok"] is True

    # Step 7: Combine & save the session!
    # Convert captured responses to CapturePayload format
    def to_payload(d):
        return {
            "arm_left_cm": d["arm_left_cm"],
            "arm_right_cm": d["arm_right_cm"],
            "shoulder_cm": d["shoulder_cm"],
            "chest_cm": d["chest_cm"],
            "waist_cm": d["waist_cm"],
            "hip_cm": d["hip_cm"],
            "thigh_left_cm": d["thigh_left_cm"],
            "thigh_right_cm": d["thigh_right_cm"],
            "arm_side_left_cm": d.get("arm_side_left_cm"),
            "arm_side_right_cm": d.get("arm_side_right_cm"),
            "thigh_side_left_cm": d.get("thigh_side_left_cm"),
            "thigh_side_right_cm": d.get("thigh_side_right_cm"),
            "chest_side_cm": d.get("chest_side_cm"),
            "waist_side_cm": d.get("waist_side_cm"),
            "hip_side_cm": d.get("hip_side_cm"),
            "confidence": d["confidence"]
        }

    combine_payload = {
        "front": to_payload(front_captured_data),
        "left_side": to_payload(left_captured_data),
        "right_side": to_payload(right_captured_data)
    }

    resp = client.post("/api/v1/measure/combine", json=combine_payload)
    assert resp.status_code == 200
    combined_data = resp.json()
    assert "pseudo3d" in combined_data
    p3d = combined_data["pseudo3d"]
    # Check all key girths are present in combined result
    for key in ("chest_girth_cm", "waist_girth_cm", "hip_girth_cm", 
                "arm_left_girth_cm", "arm_right_girth_cm", 
                "thigh_left_girth_cm", "thigh_right_girth_cm",
                "arm_asymmetry_pct", "thigh_asymmetry_pct"):
        assert p3d.get(key) is not None
        assert p3d[key] > 0 or key.endswith("pct")

    # Save session to DB
    session_payload = {
        "arm_left_cm": combined_data["front"]["arm_left_cm"],
        "arm_right_cm": combined_data["front"]["arm_right_cm"],
        "shoulder_cm": combined_data["front"]["shoulder_cm"],
        "chest_cm": combined_data["front"]["chest_cm"],
        "waist_cm": combined_data["front"]["waist_cm"],
        "hip_cm": combined_data["front"]["hip_cm"],
        "thigh_left_cm": combined_data["front"]["thigh_left_cm"],
        "thigh_right_cm": combined_data["front"]["thigh_right_cm"],
        
        "arm_side_left_cm": combined_data["left_side"]["arm_side_left_cm"],
        "thigh_side_left_cm": combined_data["left_side"]["thigh_side_left_cm"],
        "chest_side_left_cm": combined_data["left_side"]["chest_side_cm"],
        "waist_side_left_cm": combined_data["left_side"]["waist_side_cm"],
        "hip_side_left_cm": combined_data["left_side"]["hip_side_cm"],

        "arm_side_right_cm": combined_data["right_side"]["arm_side_right_cm"],
        "thigh_side_right_cm": combined_data["right_side"]["thigh_side_right_cm"],
        "chest_side_right_cm": combined_data["right_side"]["chest_side_cm"],
        "waist_side_right_cm": combined_data["right_side"]["waist_side_cm"],
        "hip_side_right_cm": combined_data["right_side"]["hip_side_cm"],

        "arm_left_girth_cm": p3d["arm_left_girth_cm"],
        "arm_right_girth_cm": p3d["arm_right_girth_cm"],
        "thigh_left_girth_cm": p3d["thigh_left_girth_cm"],
        "thigh_right_girth_cm": p3d["thigh_right_girth_cm"],
        "chest_girth_cm": p3d["chest_girth_cm"],
        "waist_girth_cm": p3d["waist_girth_cm"],
        "hip_girth_cm": p3d["hip_girth_cm"],

        "arm_left_area_cm2": p3d["arm_left_area_cm2"],
        "arm_right_area_cm2": p3d["arm_right_area_cm2"],
        "thigh_left_area_cm2": p3d["thigh_left_area_cm2"],
        "thigh_right_area_cm2": p3d["thigh_right_area_cm2"],
        "chest_area_cm2": p3d["chest_area_cm2"],
        "waist_area_cm2": p3d["waist_area_cm2"],
        "hip_area_cm2": p3d["hip_area_cm2"],

        "arm_asymmetry_pct": p3d["arm_asymmetry_pct"],
        "thigh_asymmetry_pct": p3d["thigh_asymmetry_pct"],

        "capture_confidence": combined_data["front"]["confidence"],
        "frames_averaged": 8
    }

    save_resp = client.post("/api/v1/sessions", json=session_payload)
    assert save_resp.status_code == 201

    # Step 8: Verify that we can query GET /sessions and retrieve all girths
    resp = client.get("/api/v1/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) > 0
    # The last session should be ours or we can inspect the first element (descending order)
    latest_session = sessions[0]
    # Check that all girths and profile thickness fields are populated
    assert latest_session.get("chest_girth_cm") is not None
    assert latest_session.get("waist_girth_cm") is not None
    assert latest_session.get("hip_girth_cm") is not None
    assert latest_session.get("chest_side_left_cm") is not None
    assert latest_session.get("waist_side_left_cm") is not None
    assert latest_session.get("hip_side_left_cm") is not None

    # Step 9: Verify GET /predict returns predicted values
    resp = client.get("/api/v1/predict")
    assert resp.status_code == 200
    predictions = resp.json()
    assert predictions["status"] == "insufficient_data"
    assert "Need at least 5 valid sessions" in predictions["message"]

    # Step 10: Insert 4 more valid sessions to trigger successful prediction
    for i in range(4):
        payload = session_payload.copy()
        payload["chest_girth_cm"] = session_payload["chest_girth_cm"] - (4 - i) * 0.5
        payload["waist_girth_cm"] = session_payload["waist_girth_cm"] - (4 - i) * 0.5
        payload["hip_girth_cm"] = session_payload["hip_girth_cm"] - (4 - i) * 0.5
        save_resp = client.post("/api/v1/sessions", json=payload)
        assert save_resp.status_code == 201

    # Step 11: Verify GET /predict now returns status "ok" and full trajectory details
    resp = client.get("/api/v1/predict")
    assert resp.status_code == 200
    predictions = resp.json()
    assert predictions["status"] == "ok"
    assert "confidence" in predictions
    assert "history_chart" in predictions
    assert "prediction_chart" in predictions
    assert "body_comp_insights" in predictions


def test_physiological_validations():
    client = TestClient(app)

    # 1. Torso width > shoulder_width * 1.8 in front frame mode validation
    lms = make_landmarks(side_mode=False)
    serialized_lms = [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in lms]

    resp = client.post("/api/v1/measure/frame", json={
        "height_cm": 175,
        "landmarks": serialized_lms,
        "video_width": 640,
        "video_height": 480,
        "mode": "front",
        "silhouette_chest_px": 300.0, # extremely wide compared to synthetic shoulders
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["validation"]["ok"] is False
    assert "Measurement invalid. Torso detection failed. Please retake scan." in data["validation"]["reason"]

    # 1.5. Suspicious waist validation check: waist_px > shoulder_px * 1.15
    resp = client.post("/api/v1/measure/frame", json={
        "height_cm": 175,
        "landmarks": serialized_lms,
        "video_width": 640,
        "video_height": 480,
        "mode": "front",
        "silhouette_waist_px": 125.0, # 125 > 102.4 * 1.15 = 117.76
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["validation"]["ok"] is False
    assert "Suspicious waist measurement. Please keep arms away from torso." in data["validation"]["reason"]

    # 2. Torso girth safety bounds in /combine
    combine_payload = {
        "height_cm": 175.0,
        "front": {
            "arm_left_cm": 10.0, "arm_right_cm": 10.0, "shoulder_cm": 40.0,
            "chest_cm": 250.0, "waist_cm": 80.0, "hip_cm": 90.0,
            "thigh_left_cm": 20.0, "thigh_right_cm": 20.0, "scale_cm_per_px": 0.3, "confidence": 0.95
        },
        "left_side": {
            "arm_side_left_cm": 10.0, "thigh_side_left_cm": 20.0,
            "chest_side_cm": 30.0, "waist_side_cm": 25.0, "hip_side_cm": 30.0,
            "scale_cm_per_px": 0.3, "confidence": 0.95
        },
        "right_side": {
            "arm_side_right_cm": 10.0, "thigh_side_right_cm": 20.0,
            "chest_side_cm": 30.0, "waist_side_cm": 25.0, "hip_side_cm": 30.0,
            "scale_cm_per_px": 0.3, "confidence": 0.95
        }
    }
    resp = client.post("/api/v1/measure/combine", json=combine_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["measurement_invalid"] is True
    assert "Measurement invalid. Torso detection failed. Please retake scan." in data["error_message"]


def test_sessions_physiological_rejection():
    client = TestClient(app)

    # Post session with exploding chest girth (>180 cm)
    payload = {
        "chest_cm": 46.62,
        "chest_side_left_cm": 53.93,
        "chest_side_right_cm": 100.65,
        "chest_girth_cm": 197.63,
        "waist_cm": 36.37,
        "waist_side_left_cm": 81.52,
        "waist_side_right_cm": 29.51,
        "waist_girth_cm": 145.90,
        "hip_cm": 40.34,
        "hip_side_left_cm": 31.98,
        "hip_side_right_cm": 32.62,
        "hip_girth_cm": 114.45
    }
    
    resp = client.post("/api/v1/sessions", json=payload)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail.startswith("Rejected: chest_girth_cm = 197.6 cm (> 180 cm threshold)")
    assert "side depth contamination detected" in detail

    # Post session with exploding arm girth (>80 cm)
    arm_exploding_payload = {
        "chest_cm": 40.0,
        "chest_girth_cm": 100.0,
        "waist_cm": 35.0,
        "waist_girth_cm": 90.0,
        "hip_cm": 40.0,
        "hip_girth_cm": 100.0,
        "arm_left_cm": 10.0,
        "arm_side_left_cm": 30.0,  # contaminated side depth: 30 > 2.2 * 10
        "arm_left_girth_cm": 85.0  # > 80 cm
    }
    resp = client.post("/api/v1/sessions", json=arm_exploding_payload)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "left_arm_girth_cm = 85.0 cm (outside 15.0 - 80.0 cm range)" in detail
    assert "side depth contamination detected" in detail

    # Post session with too small arm girth (<15 cm)
    arm_small_payload = {
        "chest_cm": 40.0,
        "chest_girth_cm": 100.0,
        "waist_cm": 35.0,
        "waist_girth_cm": 90.0,
        "hip_cm": 40.0,
        "hip_girth_cm": 100.0,
        "arm_left_cm": 3.0,
        "arm_left_girth_cm": 10.0  # < 15 cm
    }
    resp = client.post("/api/v1/sessions", json=arm_small_payload)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "left_arm_girth_cm = 10.0 cm (outside 15.0 - 80.0 cm range)" in detail

