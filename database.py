from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── SELLERS ──
def salvar_token(seller_id: str, seller_nickname: str, access_token: str, refresh_token: str):
    data = {
        "seller_id": seller_id,
        "seller_nickname": seller_nickname,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_atualizado_em": datetime.utcnow().isoformat(),
    }
    existing = supabase.table("sellers").select("*").eq("seller_id", seller_id).execute()
    if existing.data:
        supabase.table("sellers").update(data).eq("seller_id", seller_id).execute()
    else:
        supabase.table("sellers").insert(data).execute()

def atualizar_tokens(seller_id: str, access_token: str, refresh_token: str):
    """Atualiza apenas os tokens após renovação automática"""
    supabase.table("sellers").update({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_atualizado_em": datetime.utcnow().isoformat(),
    }).eq("seller_id", seller_id).execute()

def buscar_token(seller_id: str):
    result = supabase.table("sellers").select("*").eq("seller_id", seller_id).execute()
    if result.data:
        return result.data[0]
    return None

def listar_sellers():
    result = supabase.table("sellers").select("seller_id, seller_nickname").execute()
    return result.data

# ── CÓDIGOS DE ACESSO ──
def validar_codigo(codigo: str):
    """Verifica se o código existe e ainda não foi usado"""
    result = supabase.table("codigos_acesso").select("*").eq("codigo", codigo).execute()
    if not result.data:
        return None
    cod = result.data[0]
    if cod["usado"]:
        return None
    return cod

def marcar_codigo_usado(codigo: str, seller_id: str):
    """Marca o código como usado após o seller conectar"""
    supabase.table("codigos_acesso").update({
        "usado": True,
        "seller_id": seller_id,
        "usado_em": datetime.utcnow().isoformat()
    }).eq("codigo", codigo).execute()

def criar_codigo(codigo: str, nome_cliente: str = None):
    """Cria um novo código de acesso (usado pelo consultor)"""
    supabase.table("codigos_acesso").insert({
        "codigo": codigo,
        "nome_cliente": nome_cliente
    }).execute()

def listar_codigos():
    """Lista todos os códigos — usados e disponíveis"""
    result = supabase.table("codigos_acesso").select("*").order("criado_em", desc=True).execute()
    return result.data
