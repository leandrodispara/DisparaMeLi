from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def salvar_token(seller_id: str, seller_nickname: str, access_token: str, refresh_token: str):
    data = {
        "seller_id": seller_id,
        "seller_nickname": seller_nickname,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    existing = supabase.table("sellers").select("*").eq("seller_id", seller_id).execute()
    if existing.data:
        supabase.table("sellers").update(data).eq("seller_id", seller_id).execute()
    else:
        supabase.table("sellers").insert(data).execute()

def buscar_token(seller_id: str):
    result = supabase.table("sellers").select("*").eq("seller_id", seller_id).execute()
    if result.data:
        return result.data[0]
    return None

def listar_sellers():
    result = supabase.table("sellers").select("seller_id, seller_nickname").execute()
    return result.data
