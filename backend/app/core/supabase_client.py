# backend/app/core/supabase_client.py
from supabase import create_client, Client
from app.core.config import get_settings

# Optional admin client (service_role) for server-side reads that bypass RLS (e.g. /me by X-User-Id)
_admin_client: Client | None = None


def get_supabase() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_key)


def get_supabase_admin() -> Client | None:
    """Service role client for reading profiles by user_id (RLS blocks anon key with no JWT)."""
    global _admin_client
    s = get_settings()
    role_key = (s.supabase_service_role_key or "").strip()
    if not role_key or not (s.supabase_url or "").strip():
        return None
    if _admin_client is None:
        _admin_client = create_client(s.supabase_url, role_key)
    return _admin_client
