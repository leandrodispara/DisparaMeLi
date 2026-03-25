from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import os
import random
import string
from dotenv import load_dotenv

from auth import get_auth_url, trocar_code_por_token, renovar_token
from database import (salvar_token, buscar_token, listar_sellers,
                      validar_codigo, marcar_codigo_usado,
                      criar_codigo, listar_codigos)
from meli import get_seller_info, get_reputacao, analisar_anuncios, get_vendas_recentes
from ia import analisar_conta_com_ia

load_dotenv()

CONSULTOR_PASSWORD = os.getenv("CONSULTOR_PASSWORD", "DisparaVendas2025")

app = FastAPI(title="Dispara Vendas - Horizon MELI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# AUTENTICAÇÃO OAUTH MELI (com código de acesso)
# ─────────────────────────────────────────────

@app.get("/auth/login")
def login(codigo: str = Query(...)):
    """Valida o código de acesso e redireciona para o login do MELI"""
    cod = validar_codigo(codigo)
    if not cod:
        raise HTTPException(status_code=403, detail="Código de acesso inválido ou já utilizado.")
    # Salva o código na URL de estado para recuperar no callback
    url = get_auth_url() + f"&state={codigo}"
    return RedirectResponse(url)

@app.get("/auth/callback")
async def callback(code: str = Query(...), state: str = Query(None)):
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

# Marca o código como usado
    if state:
        marcar_codigo_usado(state, seller_id)

    frontend_url = os.getenv("FRONTEND_URL", "https://leandrodispara.github.io/DisparaMeLi")
    return RedirectResponse(f"{frontend_url}/index.html?seller_id={seller_id}")

  
@app.get("/auth/validar-codigo")
def validar_codigo_endpoint(codigo: str = Query(...)):
    """Verifica se um código é válido antes de redirecionar"""
    cod = validar_codigo(codigo)
    if not cod:
        return {"valido": False, "mensagem": "Código inválido ou já utilizado."}
    return {"valido": True, "mensagem": "Código válido!"}

# ─────────────────────────────────────────────
# ENDPOINTS DO SELLER (versão pública)
# ─────────────────────────────────────────────

@app.get("/seller/{seller_id}/resumo")
async def resumo_seller(seller_id: str):
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

@app.post("/consultor/codigos/gerar")
def gerar_codigo(quantidade: int = 1, nome_cliente: str = Query(None), auth=Depends(verificar_consultor)):
    """Gera novos códigos de acesso para sellers"""
    codigos_gerados = []
    for _ in range(quantidade):
        codigo = "DISP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        criar_codigo(codigo, nome_cliente)
        codigos_gerados.append(codigo)
    return {"codigos": codigos_gerados}

@app.get("/consultor/sellers")
def listar_todos_sellers(auth=Depends(verificar_consultor)):
    return listar_sellers()

@app.get("/consultor/seller/{seller_id}/completo")
async def analise_completa(seller_id: str, auth=Depends(verificar_consultor)):
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
    """Análise completa com IA — exclusivo para o consultor"""
    seller = buscar_token(seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller não encontrado")
    access_token = seller["access_token"]
    reputacao = await get_reputacao(seller_id, access_token)
    anuncios = await analisar_anuncios(seller_id, access_token)
    vendas = await get_vendas_recentes(seller_id, access_token)
    seller_data = {
        "nickname": seller["seller_nickname"],
        "reputacao": reputacao,
        "anuncios": anuncios,
        "vendas_recentes": vendas,
    }
    analise = await analisar_conta_com_ia(seller_data)
    return {
        "seller_id": seller_id,
        "nickname": seller["seller_nickname"],
        "analise_ia": analise,
        "dados_brutos": seller_data,
    }

# ── Gestão de Códigos de Acesso ──

@app.post("/consultor/codigos/gerar")
def gerar_codigo(quantidade: int = 1, auth=Depends(verificar_consultor)):
    """Gera novos códigos de acesso para sellers"""
    codigos_gerados = []
    for _ in range(quantidade):
        codigo = "DISP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        criar_codigo(codigo)
        codigos_gerados.append(codigo)
    return {"codigos": codigos_gerados}

@app.get("/consultor/codigos")
def ver_codigos(auth=Depends(verificar_consultor)):
    """Lista todos os códigos — disponíveis e usados"""
    return listar_codigos()

@app.get("/")
def root():
    return {"status": "Dispara Vendas - Horizon MELI API online 🚀"}
