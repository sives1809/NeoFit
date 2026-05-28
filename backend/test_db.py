import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

print("Supabase URL:", url)
client = create_client(url, key)

try:
    res = client.table("profiles").select("*").limit(5).execute()
    print("Successfully connected! Data:")
    print(res.data)
except Exception as e:
    print("Error querying profiles table:", e)
