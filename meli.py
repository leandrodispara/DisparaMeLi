import httpx

MELI_API = "https://api.mercadolibre.com"

async def get_seller_info(access_token: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{MELI_API}/users/me", headers={"Authorization": f"Bearer {access_token}"})
        return r.json()

async def get_reputacao(seller_id: str, access_token: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{MELI_API}/users/{seller_id}", headers={"Authorization": f"Bearer {access_token}"})
        data = r.json()
        reputacao = data.get("seller_reputation", {})
        nivel = reputacao.get("level_id", "Sem dados")
        transacoes = reputacao.get("transactions", {})
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
            "reclamacoes_pct": round(reclamacoes * 100, 2),
            "atrasos_pct": round(atrasos * 100, 2),
            "cancelamentos": cancelamentos,
            "alertas": alertas,
        }

async def get_anuncios(seller_id: str, access_token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async def buscar_todos(status):
            ids = []
            offset = 0
            while True:
                r = await client.get(
                    f"{MELI_API}/users/{seller_id}/items/search"
                    f"?status={status}&limit=50&offset={offset}",
                    headers=headers
                )
                data = r.json()
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
        }async def get_anuncios(seller_id: str, access_token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async def buscar_todos(status):
            ids = []
            offset = 0
            while True:
                r = await client.get(
                    f"{MELI_API}/users/{seller_id}/items/search"
                    f"?status={status}&limit=50&offset={offset}",
                    headers=headers
                )
                data = r.json()
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

async def get_detalhes_anuncio(item_id: str, access_token: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{MELI_API}/items/{item_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return r.json()

async def analisar_anuncios(seller_id: str, access_token: str):
    anuncios = await get_anuncios(seller_id, access_token)
    alertas = []
    problemas = []

    # Alertas de pausados
    if anuncios["total_pausados"] > 0:
        alertas.append(f"⚠️ Você tem {anuncios['total_pausados']} anúncio(s) pausado(s)")

    # Analisa detalhes dos ativos (até 10 para não sobrecarregar a API)
    for item_id in anuncios["ativos"][:10]:
        item = await get_detalhes_anuncio(item_id, access_token)

        titulo = item.get("title", "")
        fotos = item.get("pictures", [])
        descricao = item.get("descriptions", [])
        estoque = item.get("available_quantity", 0)
        preco = item.get("price", 0)
        frete_gratis = item.get("shipping", {}).get("free_shipping", False)

        problemas_item = []

        if len(titulo) < 40:
            problemas_item.append("Título muito curto (ideal: mais de 40 caracteres)")
        if len(fotos) < 5:
            problemas_item.append(f"Poucas fotos ({len(fotos)} foto(s) — ideal: mínimo 5)")
        if not descricao:
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
                "problemas": problemas_item
            })

    return {
        "total_ativos": len(anuncios["ativos"]),
        "total_pausados": anuncios["total_pausados"],
        "alertas_gerais": alertas,
        "anuncios_com_problema": problemas,
    }

async def get_vendas_recentes(seller_id: str, access_token: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{MELI_API}/orders/search?seller={seller_id}&sort=date_desc&limit=50",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return r.json()
