from app.database import supabase

def log_action(user_id, action, result):

    supabase.table("audit_logs").insert({
        "user_id": user_id,
        "action": action,
        "result": result
    }).execute()