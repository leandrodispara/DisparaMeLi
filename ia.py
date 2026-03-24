import httpx
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

async def analisar_conta_com_ia(seller_data: dict) -> str:
    """
    Recebe todos os dados do seller e retorna uma análise
    completa e personalizada gerada pelo Claude.
    """

    nickname = seller_data.get("nickname", "Seller")
    reputacao = seller_data.get("reputacao", {})
    anuncios = seller_data.get("anuncios", {})
    vendas = seller_data.get("vendas_recentes", {})

    # Monta o prompt com todos os dados do seller
    prompt = f"""
Você é um consultor especialista em Mercado Livre com mais de 10 anos de experiência.
Analise os dados abaixo do seller "{nickname}" e gere um relatório de consultoria completo e personalizado.

## DADOS DA CONTA

### Reputação
- Nível atual: {reputacao.get('nivel', 'N/A')}
- Taxa de reclamações: {reputacao.get('reclamacoes_pct', 0)}%
- Taxa de atrasos no envio: {reputacao.get('atrasos_pct', 0)}%
- Cancelamentos: {reputacao.get('cancelamentos', 0)}
- Alertas identificados: {reputacao.get('alertas', [])}

### Anúncios
- Total de anúncios ativos: {anuncios.get('total_ativos', 0)}
- Total de anúncios pausados: {anuncios.get('total_pausados', 0)}
- Alertas gerais: {anuncios.get('alertas_gerais', [])}
- Anúncios com problema: {anuncios.get('anuncios_com_problema', [])}

### Vendas Recentes
{vendas}

## INSTRUÇÕES

Gere um relatório de consultoria com as seguintes seções:

1. **📊 Diagnóstico Geral** — Avalie a saúde geral da conta em uma escala de 0 a 10 e explique o porquê.

2. **🚨 Problemas Críticos** — Liste os problemas mais urgentes que precisam ser resolvidos AGORA, com explicação do impacto de cada um.

3. **📈 Plano de Ação** — Liste de 3 a 5 ações prioritárias e práticas, ordenadas por impacto, com instruções claras de como executar cada uma dentro do Mercado Livre.

4. **💡 Oportunidades Identificadas** — Aponte 2 a 3 oportunidades que o seller não está aproveitando e como explorar cada uma.

5. **⚠️ Alertas do Consultor** — Observações importantes que apenas um especialista perceberia nesses dados.

Seja direto, prático e use linguagem simples. Evite termos técnicos sem explicação.
O seller é brasileiro, então escreva em português do Brasil.
"""

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(ANTHROPIC_URL, headers=headers, json=body)
        data = response.json()

        if "content" in data and len(data["content"]) > 0:
            return data["content"][0]["text"]
        else:
            raise Exception(f"Erro na API da IA: {data}")
