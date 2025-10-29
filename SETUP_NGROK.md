# 🚇 Setup ngrok - Guia Completo

Este guia configura o ngrok como serviço systemd resiliente.

---

## 📋 O que Será Configurado

- ✅ Serviço ngrok (`ngrok-tunnel.service`)
- ✅ Auto-start no boot
- ✅ Auto-restart se cair
- ✅ Logs persistentes

---

## 🚀 Instalação Rápida

### 1. Enviar Arquivos para VM

**Do seu PC (PowerShell):**

```powershell
# Enviar arquivos de serviço ngrok
scp "D:\Users\rafa2\OneDrive\Desktop\monitoramento_vaga\ngrok-tunnel.service" rafaelsantis@35.198.44.137:~/ccr-backend/
scp "D:\Users\rafa2\OneDrive\Desktop\monitoramento_vaga\setup-ngrok-service.sh" rafaelsantis@35.198.44.137:~/ccr-backend/
```

### 2. Atualizar .env com URL do ngrok

**Conectar na VM:**

```powershell
ssh rafaelsantis@35.198.44.137
```

**Na VM:**

```bash
cd ~/ccr-backend

# Atualizar STREAM_BASE_URL com URL do ngrok
sed -i 's|STREAM_BASE_URL=.*|STREAM_BASE_URL=https://93340ef8d764.ngrok-free.app|' .env

# Verificar
cat .env | grep STREAM_BASE_URL

# Reiniciar Flask
sudo systemctl restart parking-api.service
```

### 3. Instalar Serviço ngrok

**Na VM:**

```bash
cd ~/ccr-backend

# Dar permissão de execução
chmod +x setup-ngrok-service.sh

# Executar instalação
./setup-ngrok-service.sh
```

### 4. Verificar URL do ngrok

**Na VM:**

```bash
# Ver URL do ngrok
sudo journalctl -u ngrok-tunnel.service | grep -E "url=.*ngrok" | tail -1

# OU ver logs em tempo real
sudo journalctl -u ngrok-tunnel.service -f
```

**A URL do ngrok aparecerá assim:**
```
url=https://XXXXXXXX.ngrok-free.app
```

---

## 🔧 Comandos Úteis

### Verificar Status

```bash
sudo systemctl status ngrok-tunnel.service
```

### Ver Logs

```bash
# Logs em tempo real
sudo journalctl -u ngrok-tunnel.service -f

# Últimos 50 logs
sudo journalctl -u ngrok-tunnel.service -n 50

# Ver URL
sudo journalctl -u ngrok-tunnel.service | grep -E "url=.*ngrok" | tail -1
```

### Controlar Serviço

```bash
# Reiniciar
sudo systemctl restart ngrok-tunnel.service

# Parar
sudo systemctl stop ngrok-tunnel.service

# Iniciar
sudo systemctl start ngrok-tunnel.service

# Desabilitar auto-start
sudo systemctl disable ngrok-tunnel.service
```

---

## ⚠️ IMPORTANTE: URL do ngrok Muda!

Toda vez que você reiniciar o serviço ngrok, **a URL muda**.

Quando isso acontecer, você precisa:

1. **Atualizar .env no Backend:**

```bash
# Pegar nova URL
sudo journalctl -u ngrok-tunnel.service | grep -E "url=.*ngrok" | tail -1

# Atualizar .env (substitua <nova-url> pela URL)
sed -i 's|STREAM_BASE_URL=.*|STREAM_BASE_URL=<nova-url>|' ~/ccr-backend/.env

# Reiniciar Flask
sudo systemctl restart parking-api.service
```

2. **Atualizar Vercel:**

- Acesse: https://vercel.com/seu-projeto/settings/environment-variables
- Edite `VITE_API_URL`
- Mude para a nova URL do ngrok
- Redeploy o frontend

---

## 🌐 Atualizar Vercel

Após configurar o ngrok, atualize o Vercel:

1. Acesse: https://vercel.com
2. Entre no projeto `monitoramento-vaga`
3. Settings → Environment Variables
4. Edite `VITE_API_URL`
5. Valor: `https://93340ef8d764.ngrok-free.app` (ou URL atual)
6. Save
7. Redeploy: Deployments → ... → Redeploy

---

## 📝 Workaround do Header ngrok

O frontend foi configurado para enviar o header `ngrok-skip-browser-warning: true` em todas as requisições, evitando a página de aviso do ngrok free tier.

**Arquivos modificados:**
- `frontend/src/config.ts` - Criado helper `apiFetch`
- `frontend/src/pages/Videowall.tsx` - Usa `apiFetch`
- `frontend/src/pages/CameraConfig.tsx` - Usa `apiFetch`
- `frontend/src/pages/CameraAreas.tsx` - Usa `apiFetch`

---

## ✅ Checklist

Após instalação:

- [ ] Serviço ngrok rodando: `sudo systemctl status ngrok-tunnel.service`
- [ ] URL do ngrok acessível: `curl https://XXXXXXXX.ngrok-free.app/api/cameras`
- [ ] .env atualizado com URL do ngrok
- [ ] Flask reiniciado após atualizar .env
- [ ] Vercel atualizado com URL do ngrok
- [ ] Frontend faz deploy no Vercel
- [ ] Frontend acessa API sem erro

---

## 🐛 Troubleshooting

### Serviço não inicia

```bash
# Ver erros
sudo journalctl -u ngrok-tunnel.service -p err -n 50

# Verificar se ngrok está instalado
which ngrok

# Verificar authtoken
cat ~/.config/ngrok/ngrok.yml
```

### URL não aparece nos logs

```bash
# Espere 10 segundos para o ngrok conectar
sleep 10

# Tente novamente
sudo journalctl -u ngrok-tunnel.service | grep -E "url=.*ngrok" | tail -1
```

### Frontend não acessa API

1. Verifique se URL do Vercel está correta
2. Teste com PowerShell:
   ```powershell
   $headers = @{"ngrok-skip-browser-warning" = "true"}
   Invoke-RestMethod -Uri "https://XXXXXXXX.ngrok-free.app/api/cameras" -Headers $headers
   ```
3. Verifique console do navegador (F12)

---

**Última Atualização:** 2025-10-29
**Versão:** 1.0
