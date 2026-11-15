from typing import Any, Optional
from supabase import Client, create_client
from app.core.config import settings

WALLET_BUCKET_NAME = "health-wallet-private"
SIGNED_URL_TTL_SECONDS = 60  # Strict 60-second expiry for viewing medical documents

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Singleton initializer for Supabase service client."""
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise RuntimeError("Supabase credentials are not configured in environment.")
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _supabase_client


def generate_private_wallet_signed_url(storage_client: Any, file_path: str) -> str:
    """
    Generates a temporary 60-second signed URL for a private medical document
    so neither doctors nor caretakers ever receive permanent public file links.
    """
    res = storage_client.from_(WALLET_BUCKET_NAME).create_signed_url(
        file_path, SIGNED_URL_TTL_SECONDS
    )
    if isinstance(res, dict) and "signedURL" in res:
        return res["signedURL"]
    raise ValueError("Failed to generate signed URL from private storage bucket.")