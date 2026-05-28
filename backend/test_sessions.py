import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

client = create_client(url, key)
user_id = "1eed0d2f-895b-4f9a-856a-9e059809eb6c"

try:
    res = client.table("sessions").select("*").eq("user_id", user_id).order("captured_at", desc=True).execute()
    print("Found", len(res.data), "sessions for user", user_id)
    for s in res.data:
        print(f"Session {s.get('id')} ({s.get('captured_at')})")
        print(f"  Chest: front={s.get('chest_cm')}, side_L={s.get('chest_side_left_cm')}, side_R={s.get('chest_side_right_cm')}, girth={s.get('chest_girth_cm')}")
        print(f"  Waist: front={s.get('waist_cm')}, side_L={s.get('waist_side_left_cm')}, side_R={s.get('waist_side_right_cm')}, girth={s.get('waist_girth_cm')}")
        print(f"  Hip:   front={s.get('hip_cm')}, side_L={s.get('hip_side_left_cm')}, side_R={s.get('hip_side_right_cm')}, girth={s.get('hip_girth_cm')}")
        print("-" * 50)
except Exception as e:
    print("Error querying sessions table:", e)
