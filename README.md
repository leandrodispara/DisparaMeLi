# Dispara Vendas — Horizon MELI Backend

API backend do sistema Horizon MELI, construída com FastAPI.

## 🚀 Como rodar localmente

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## ⚙️ Variáveis de ambiente (.env)

Crie um arquivo `.env` na raiz com:

```
MELI_CLIENT_ID=seu_client_id
MELI_CLIENT_SECRET=seu_client_secret
MELI_REDIRECT_URI=sua_redirect_uri
SUPABASE_URL=sua_url_supabase
SUPABASE_KEY=sua_key_supabase
CONSULTOR_PASSWORD=sua_senha_consultor
FRONTEND_URL=https://seu-frontend.vercel.app
WHATSAPP_NUMBER=5544991030610
```

## 📦 Deploy no Render

1. Suba o projeto no GitHub (sem o .env!)
2. Crie um novo Web Service no Render
3. Conecte o repositório
4. Em "Environment Variables", adicione todas as variáveis acima
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `uvicorn main:app --host 0.0.0.0 --port 10000`

## 🗄️ Tabela necessária no Supabase

Execute este SQL no Supabase:

```sql
CREATE TABLE sellers (
  id SERIAL PRIMARY KEY,
  seller_id TEXT UNIQUE NOT NULL,
  seller_nickname TEXT,
  access_token TEXT,
  refresh_token TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## 📡 Endpoints

### Seller (público)
- `GET /auth/login` — inicia o login OAuth
- `GET /auth/callback` — callback OAuth
- `GET /seller/{seller_id}/resumo` — resumo completo
- `GET /seller/{seller_id}/reputacao` — reputação
- `GET /seller/{seller_id}/anuncios` — análise de anúncios

### Consultor (protegido)
- `GET /consultor/sellers?senha=...` — lista todos os sellers
- `GET /consultor/seller/{seller_id}/completo?senha=...` — análise completa
