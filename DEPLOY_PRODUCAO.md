# 🚀 Deploy em Produção - Sistema de Monitoramento de Vagas

## 📋 Pré-requisitos

- VM no GCP com GPU T4
- Conta Supabase
- Conta Vercel
- Cloudflare Tunnel configurado

---

## 1️⃣ Configurar Banco de Dados Supabase

### 1.1 Executar Migração de Schema

Acesse o SQL Editor do Supabase e execute:

```sql
-- Arquivo: add_stream_url_migration.sql
ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS stream_url TEXT;

COMMENT ON COLUMN cameras.stream_url IS 'URL pública do stream processado (ex: Cloudflare Tunnel URL)';

-- Atualizar a view
CREATE OR REPLACE VIEW camera_stats_realtime AS
SELECT
    c.id,
    c.name,
    c.location,
    c.status,
    c.stream_url,
    c.areas_count,
    oh.occupied_spots,
    oh.free_spots,
    oh.total_spots,
    oh.occupancy_percentage,
    oh.fps,
    oh.timestamp as last_update
FROM cameras c
LEFT JOIN LATERAL (
    SELECT * FROM occupancy_history
    WHERE camera_id = c.id
    ORDER BY timestamp DESC
    LIMIT 1
) oh ON true;
```

---

## 2️⃣ Configurar Backend na VM do GCP

### 2.1 Clonar Repositório

```bash
cd ~
git clone <seu-repositorio>
cd monitoramento_vaga
```

### 2.2 Configurar Ambiente Virtual

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.3 Configurar Variáveis de Ambiente

Crie o arquivo `.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://rvfrxbcirqonkzfbpyfh.supabase.co
SUPABASE_KEY=<sua-service-role-key>

# Flask Configuration
FLASK_DEBUG=False
FLASK_PORT=5000

# Streaming Configuration
# ⚠️ IMPORTANTE: Atualize com sua URL do Cloudflare Tunnel
STREAM_BASE_URL=https://apparent-pichunter-symptoms-recorders.trycloudflare.com
```

### 2.4 Instalar Cloudflare Tunnel

```bash
# Baixar e instalar
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### 2.5 Iniciar Backend

```bash
# Rodar Flask em background
nohup python api_server.py > api.log 2>&1 &

# Rodar Cloudflare Tunnel em background
nohup cloudflared tunnel --url http://localhost:5000 > cloudflared.log 2>&1 &
```

### 2.6 Obter URL do Cloudflare Tunnel

```bash
# Verificar logs para pegar a URL
tail -f cloudflared.log

# Exemplo de saída:
# https://apparent-pichunter-symptoms-recorders.trycloudflare.com
```

⚠️ **IMPORTANTE**: Copie essa URL e atualize:
1. No arquivo `.env` na variável `STREAM_BASE_URL`
2. Reinicie o Flask: `pkill -f api_server.py && nohup python api_server.py > api.log 2>&1 &`

---

## 3️⃣ Configurar Frontend na Vercel

### 3.1 Fazer Push do Código

```bash
git add .
git commit -m "feat: Add stream_url persistence and fix CORS"
git push origin main
```

### 3.2 Configurar Variáveis de Ambiente na Vercel

1. Acesse: https://vercel.com/seu-projeto/settings/environment-variables
2. Adicione a variável:

```
Name: VITE_API_URL
Value: https://apparent-pichunter-symptoms-recorders.trycloudflare.com
Environments: ✅ Production ✅ Preview ✅ Development
```

### 3.3 Fazer Redeploy

1. Vá em: https://vercel.com/seu-projeto/deployments
2. Clique nos 3 pontinhos do último deploy
3. Clique em **"Redeploy"**

---

## 4️⃣ Verificar Instalação

### 4.1 Testar Backend

```bash
# Do seu PC local
curl https://apparent-pichunter-symptoms-recorders.trycloudflare.com/api/cameras
```

Deve retornar JSON com as câmeras.

### 4.2 Testar Frontend

Acesse: https://front-end-costa-silva-ccr-poc-tkkg.vercel.app

Deve mostrar as câmeras e streams funcionando.

### 4.3 Verificar Logs

```bash
# Na VM do GCP

# Logs do Flask
tail -f ~/monitoramento_vaga/api.log

# Logs do Cloudflare Tunnel
tail -f ~/monitoramento_vaga/cloudflared.log
```

---

## 5️⃣ Manutenção

### Reiniciar Backend

```bash
# Matar processos
pkill -f api_server.py
pkill -f cloudflared

# Reiniciar
cd ~/monitoramento_vaga
source venv/bin/activate
nohup python api_server.py > api.log 2>&1 &
nohup cloudflared tunnel --url http://localhost:5000 > cloudflared.log 2>&1 &

# ⚠️ Se a URL do Cloudflare Tunnel mudou, atualize:
# 1. .env -> STREAM_BASE_URL
# 2. Vercel -> VITE_API_URL
# 3. Reinicie Flask novamente
```

### Verificar Status dos Processos

```bash
# Flask
ps aux | grep api_server.py

# Cloudflare Tunnel
ps aux | grep cloudflared

# Porta 5000
sudo netstat -tuln | grep 5000
```

### Monitorar GPU

```bash
nvidia-smi -l 1
```

---

## 🔧 Troubleshooting

### Erro de CORS

Se aparecer erro de CORS no frontend:

1. Verifique se o domínio da Vercel está no array `origins` em `api_server.py` (linha 28-32)
2. Reinicie o Flask

### Stream não aparece

1. Verifique se a câmera está com status "online" no banco
2. Verifique se a `stream_url` está preenchida no Supabase
3. Teste a URL diretamente no navegador

### Cloudflare Tunnel caiu

```bash
# Verificar se está rodando
ps aux | grep cloudflared

# Se não estiver, reiniciar
nohup cloudflared tunnel --url http://localhost:5000 > cloudflared.log 2>&1 &
```

---

## 📊 Arquitetura Final

```
[Cliente Browser]
       ↓
[Vercel Frontend] → [Cloudflare Tunnel] → [GCP VM Backend]
       ↓                                           ↓
[Supabase Database] ←──────────────────────────────┘
```

---

## ✅ Checklist de Deploy

- [ ] Migração SQL executada no Supabase
- [ ] Backend rodando na VM do GCP
- [ ] Cloudflare Tunnel ativo
- [ ] `.env` configurado com STREAM_BASE_URL correto
- [ ] Frontend deployado na Vercel
- [ ] VITE_API_URL configurado na Vercel
- [ ] Teste de API funcionando
- [ ] Frontend mostrando câmeras
- [ ] Streams de vídeo aparecendo
- [ ] Dados sendo salvos no Supabase

---

## 🎯 O que foi Implementado

### Backend
- ✅ CORS configurado para Vercel
- ✅ Variável de ambiente `STREAM_BASE_URL`
- ✅ Método `update_camera_stream_url` no Supabase client
- ✅ Atualização automática de `stream_url` ao iniciar câmeras
- ✅ Endpoint `/api/cameras` retorna `stream_url`

### Frontend
- ✅ Interface `Camera` com campo `stream_url`
- ✅ Componente Videowall usa `stream_url` do banco
- ✅ Fallback para URL construída se `stream_url` não existir

### Banco de Dados
- ✅ Campo `stream_url` na tabela `cameras`
- ✅ View `camera_stats_realtime` atualizada

---

**Data de Criação**: 2025-10-27
**Versão**: 1.0
