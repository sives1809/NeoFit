#!/usr/bin/env python
import os
import sys

# Add backend app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.supabase_client import get_supabase_client

def main():
    print("=== Starting NeoFit Corrupted Sessions Cleanup ===")
    try:
        db = get_supabase_client()
        
        print("Running deletion for chest_girth_cm > 200...")
        res1 = db.table("sessions").delete().gt("chest_girth_cm", 200).execute()
        
        print("Running deletion for waist_girth_cm > 200...")
        res2 = db.table("sessions").delete().gt("waist_girth_cm", 200).execute()
        
        print("Running deletion for hip_girth_cm > 200...")
        res3 = db.table("sessions").delete().gt("hip_girth_cm", 200).execute()
        
        print("Running deletion for arm_left_girth_cm > 80...")
        res4 = db.table("sessions").delete().gt("arm_left_girth_cm", 80).execute()
        
        print("Running deletion for arm_right_girth_cm > 80...")
        res5 = db.table("sessions").delete().gt("arm_right_girth_cm", 80).execute()
        
        print("Running deletion for thigh_left_girth_cm > 100...")
        res6 = db.table("sessions").delete().gt("thigh_left_girth_cm", 100).execute()
        
        print("Running deletion for thigh_right_girth_cm > 100...")
        res7 = db.table("sessions").delete().gt("thigh_right_girth_cm", 100).execute()
        
        deleted_count = 0
        for res in [res1, res2, res3, res4, res5, res6, res7]:
            if res and getattr(res, "data", None):
                deleted_count += len(res.data)
                
        print(f"Cleanup finished successfully. Total deleted sessions: {deleted_count}")
    except Exception as e:
        print(f"Error during cleanup: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
