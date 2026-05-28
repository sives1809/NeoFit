import urllib.request
import json
import sys

# 1. We just want to see if the server responds or hangs, and if it responds with 422 or 401.
# Hit /measure/frame with a dummy token and payload
data = {
    'landmarks': [{'x':0.5, 'y':0.5, 'z':0, 'visibility':1.0}] * 33,
    'height_cm': 175,
    'video_width': 640,
    'video_height': 480,
    'mode': 'front'
}
payload = json.dumps(data).encode('utf-8')
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer test_token'
}

req2 = urllib.request.Request("http://127.0.0.1:8000/api/v1/measure/frame", data=payload, headers=headers)
try:
    resp2 = urllib.request.urlopen(req2)
    print("SUCCESS:", resp2.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
