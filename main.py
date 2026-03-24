from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import os
from dotenv import load_dotenv

from auth import get_auth_url, trocar_code_por_token, renovar_token
from database import salvar_token, buscar_token, listar_sellers
from meli import get_seller_info, get_reputacao, analisar_anuncios, get_vendas_recentes
from ia import analisar_conta_com_ia

load_dotenv()

CONSULTOR_PASSWORD = os.getenv("CONSULTOR_PASSWORD", "DisparaVendas2025")

app = FastAPI(title="Dispara Vendas - Horizon MELI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trocar pelo domínio do frontend depois
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# AUTENTICAÇÃO OAUTH MELI
# ─────────────────────────────────────────────

@app.get("/auth/login")
def login():
    """Redireciona o seller para o login do Mercado Livre"""
    url = get_auth_url()
    return RedirectResponse(url)

@app.get("/auth/callback")
async def callback(code: str = Query(...)):
    """Recebe o code do MELI e troca pelo token"""
    tokens = await trocar_code_por_token(code)
    if "access_token" not in tokens:
        raise HTTPException(status_code=400, detail="Erro ao obter token do MELI")

    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token", "")

    info = await get_seller_info(access_token)
    seller_id = str(info.get("id"))
    nickname = info.get("nickname", "Desconhecido")

    salvar_token(seller_id, nickname, access_token, refresh_token)

    # Redireciona para o dashboard do frontend com o seller_id
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/dashboard?seller_id={seller_id}")

# ─────────────────────────────────────────────
# ENDPOINTS DO SELLER (versão pública)
# ─────────────────────────────────────────────

@app.get("/seller/{seller_id}/resumo")
async def resumo_seller(seller_id: str):
    """Retorna resumo completo da conta do seller"""
    seller = buscar_token(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller não encontrado")

    access_token = seller["access_token"]

    reputacao = await get_reputacao(seller_id, access_token)
    anuncios = await analisar_anuncios(seller_id, access_token)

    return {
        "seller_id": seller_id,
        "nickname": seller["seller_nickname"],
        "reputacao": reputacao,
        "anuncios": anuncios,
    }

@app.get("/seller/{seller_id}/reputacao")
async def reputacao_seller(seller_id: str):
    seller = buscar_token(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller não encontrado")
    return await get_reputacao(seller_id, seller["access_token"])

@app.get("/seller/{seller_id}/anuncios")
async def anuncios_seller(seller_id: str):
    seller = buscar_token(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller não encontrado")
    return await analisar_anuncios(seller_id, seller["access_token"])

# ─────────────────────────────────────────────
# ENDPOINTS DO CONSULTOR (protegidos por senha)
# ─────────────────────────────────────────────

def verificar_consultor(senha: str = Query(...)):
    if senha != CONSULTOR_PASSWORD:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return True

@app.get("/consultor/sellers")
def listar_todos_sellers(auth=Depends(verificar_consultor)):
    """Lista todos os sellers conectados"""
    return listar_sellers()

@app.get("/consultor/seller/{seller_id}/completo")
async def analise_completa(seller_id: str, auth=Depends(verificar_consultor)):
    """Análise completa do seller para o consultor"""
    seller = buscar_token(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller não encontrado")

    access_token = seller["access_token"]

    reputacao = await get_reputacao(seller_id, access_token)
    anuncios = await analisar_anuncios(seller_id, access_token)
    vendas = await get_vendas_recentes(seller_id, access_token)

    return {
        "seller_id": seller_id,
        "nickname": seller["seller_nickname"],
        "reputacao": reputacao,
        "anuncios": anuncios,
        "vendas_recentes": vendas,
    }

@app.get("/consultor/seller/{seller_id}/analise-ia")
async def analise_ia(seller_id: str, auth=Depends(verificar_consultor)):
    """
    Gera análise completa e inteligente do seller usando Claude AI.
    Exclusivo para o consultor — não disponível para sellers.
    """
    seller = buscar_token(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller não encontrado")

    access_token = seller["access_token"]

    # Coleta todos os dados do seller
    reputacao = await get_reputacao(seller_id, access_token)
    anuncios = await analisar_anuncios(seller_id, access_token)
    vendas = await get_vendas_recentes(seller_id, access_token)

    seller_data = {
        "nickname": seller["seller_nickname"],
        "reputacao": reputacao,
        "anuncios": anuncios,
        "vendas_recentes": vendas,
    }

    # Envia para o Claude analisar
    analise = await analisar_conta_com_ia(seller_data)

    return {
        "seller_id": seller_id,
        "nickname": seller["seller_nickname"],
        "analise_ia": analise,
        "dados_brutos": seller_data,
    }

@app.get("/")
def root():
    return {"status": "Dispara Vendas - Horizon MELI API online 🚀"}
