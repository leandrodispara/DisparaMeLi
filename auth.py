import httpx
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("MELI_CLIENT_ID")
CLIENT_SECRET = os.getenv("MELI_CLIENT_SECRET")
REDIRECT_URI = os.getenv("MELI_REDIRECT_URI")

MELI_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
MELI_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

def get_auth_url():
    return (
        f"{MELI_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )

async def trocar_code_por_token(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(MELI_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        })
        return response.json()

async def renovar_token(refresh_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(MELI_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
        })
        return response.json()
