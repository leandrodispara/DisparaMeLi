import httpx
import os
from dotenv import load_dotenv

load_dotenv()

MELI_API = "https://api.mercadolibre.com"
MELI_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
CLIENT_ID = os.getenv("MELI_CLIENT_ID")
CLIENT_SECRET = os.getenv("MELI_CLIENT_SECRET")


async def renovar_access_token(refresh_token: str) -> dict:
    """Renova o access_token usando o refresh_token"""
    async with httpx.AsyncClient() as client:
        r = await client.post(MELI_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
        })
        return r.json()


async def chamar_api(url: str, seller_id: str, access_token: str, refresh_token: str = "") -> tuple:
    """
    Faz chamada GET à API do MELI com renovação automática de token.
    Retorna (dados, access_token_atual)
    """
    from database import atualizar_tokens

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(url, headers=headers)

            # Resposta vazia
            if not r.content:
                return {}, access_token

            if r.status_code == 401 and refresh_token:
                novos = await renovar_access_token(refresh_token)
                if "access_token" in novos:
                    novo_access = novos["access_token"]
                    novo_refresh = novos.get("refresh_token", refresh_token)
                    atualizar_tokens(seller_id, novo_access, novo_refresh)
                    r2 = await client.get(url, headers={"Authorization": f"Bearer {novo_access}"})
                    if not r2.content:
                        return {}, novo_access
                    return r2.json(), novo_access
                else:
                    return {"error": "token_expired"}, access_token

            try:
                return r.json(), access_token
            except Exception:
                return {}, access_token

        except Exception as e:
            return {"error": str(e)}, access_token


async def get_seller_info(access_token: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{MELI_API}/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return r.json()


async def get_reputacao(seller_id: str, access_token: str, refresh_token: str = ""):
    data, _ = await chamar_api(
        f"{MELI_API}/users/{seller_id}",
        seller_id, access_token, refresh_token
    )

    reputacao = data.get("seller_reputation", {})
    nivel = reputacao.get("level_id", "Sem dados")
    transacoes = reputacao.get("transactions", {})
    total_vendas = transacoes.get("total", 0)
    cancelamentos = transacoes.get("canceled", 0)
    reclamacoes = reputacao.get("metrics", {}).get("claims", {}).get("rate", 0)
    atrasos = reputacao.get("metrics", {}).get("delayed_handling_time", {}).get("rate", 0)

    alertas = []
    if reclamacoes > 0.02:
        alertas.append(f"⚠️ Taxa de reclamações alta: {round(reclamacoes*100, 1)}% (ideal abaixo de 2%)")
    if atrasos > 0.05:
        alertas.append(f"⚠️ Atrasos no envio: {round(atrasos*100, 1)}% (ideal abaixo de 5%)")
    if cancelamentos > 5:
        alertas.append(f"⚠️ Muitos cancelamentos: {cancelamentos} pedidos cancelados")

    return {
        "nivel": nivel,
        "total_vendas": total_vendas,
        "reclamacoes_pct": round(reclamacoes * 100, 2),
        "atrasos_pct": round(atrasos * 100, 2),
        "cancelamentos": cancelamentos,
        "alertas": alertas,
    }


async def get_anuncios(seller_id: str, access_token: str, refresh_token: str = ""):
    current_token = access_token

    async def buscar_todos(status):
        nonlocal current_token
        ids = []
        offset = 0
        while True:
            url = f"{MELI_API}/users/{seller_id}/items/search?status={status}&limit=50&offset={offset}"
            data, current_token = await chamar_api(url, seller_id, current_token, refresh_token)
            resultados = data.get("results", [])
            ids.extend(resultados)
            total = data.get("paging", {}).get("total", 0)
            offset += 50
            if offset >= total or not resultados:
                break
        return ids

    ativos = await buscar_todos("active")
    pausados = await buscar_todos("paused")

    return {
        "ativos": ativos,
        "pausados": pausados,
        "total_pausados": len(pausados)
    }


async def get_detalhes_anuncio(item_id: str, access_token: str, refresh_token: str = "", seller_id: str = ""):
    data, _ = await chamar_api(
        f"{MELI_API}/items/{item_id}",
        seller_id, access_token, refresh_token
    )
    return data


async def analisar_anuncios(seller_id: str, access_token: str, refresh_token: str = ""):
    anuncios = await get_anuncios(seller_id, access_token, refresh_token)
    alertas = []
    problemas = []

    if anuncios["total_pausados"] > 0:
        alertas.append(f"⚠️ Você tem {anuncios['total_pausados']} anúncio(s) pausado(s)")

    for item_id in anuncios["ativos"][:50]:
        item = await get_detalhes_anuncio(item_id, access_token, refresh_token, seller_id)

        titulo = item.get("title", "")
        fotos = item.get("pictures", [])
        estoque = item.get("available_quantity", 0)
        preco = item.get("price", 0)
        frete_gratis = item.get("shipping", {}).get("free_shipping", False)
        permalink = item.get("permalink", f"https://www.mercadolivre.com.br/p/{item_id}")
        sku = item.get("seller_custom_field", "") or ""

        # Busca descrição separadamente
        desc_data, _ = await chamar_api(
            f"{MELI_API}/items/{item_id}/descriptions",
            seller_id, access_token, refresh_token
        )
        tem_descricao = False
        if isinstance(desc_data, list) and len(desc_data) > 0:
            texto = desc_data[0].get("plain_text", "") or desc_data[0].get("text", "")
            tem_descricao = bool(texto and texto.strip())
        elif isinstance(desc_data, dict):
            texto = desc_data.get("plain_text", "") or desc_data.get("text", "")
            tem_descricao = bool(texto and texto.strip())

        problemas_item = []

        if len(titulo) < 40:
            problemas_item.append("Título muito curto (ideal: mais de 40 caracteres)")
        if len(fotos) < 8:
            problemas_item.append(f"Poucas fotos ({len(fotos)} foto(s) — ideal: mínimo 8, tamanho 1200x1200px)")
        if not tem_descricao:
            problemas_item.append("Sem descrição no anúncio")
        if estoque <= 2:
            problemas_item.append(f"⚠️ Estoque baixo: apenas {estoque} unidade(s)")
        if not frete_gratis and preco < 79:
            problemas_item.append("Considere frete grátis — produtos abaixo de R$79 têm menos visibilidade sem ele")

        if problemas_item:
            problemas.append({
                "id": item_id,
                "titulo": titulo,
                "preco": preco,
                "fotos": len(fotos),
                "estoque": estoque,
                "permalink": permalink,
                "sku": sku,
                "problemas": problemas_item
            })

    return {
        "total_ativos": len(anuncios["ativos"]),
        "total_pausados": anuncios["total_pausados"],
        "alertas_gerais": alertas,
        "anuncios_com_problema": problemas,
    }


async def get_vendas_recentes(seller_id: str, access_token: str, refresh_token: str = ""):
    todos = []
    offset = 0
    current_token = access_token
    while len(todos) < 200:
        url = f"{MELI_API}/orders/search?seller={seller_id}&sort=date_desc&limit=50&offset={offset}"
        data, current_token = await chamar_api(url, seller_id, current_token, refresh_token)
        resultados = data.get("results", [])
        todos.extend(resultados)
        total = data.get("paging", {}).get("total", 0)
        offset += 50
        if offset >= total or not resultados:
            break
    return {"results": todos, "paging": {"total": len(todos)}}
