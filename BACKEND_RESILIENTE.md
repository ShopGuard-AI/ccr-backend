# 🛡️ Backend Resiliente - Configuração de Serviços

Este guia configura o backend para rodar 24/7 com auto-restart automático.

---

## 🎯 O que será Configurado

✅ **Serviço Flask API** (`parking-api.service`)
- Inicia automaticamente no boot
- Reinicia automaticamente se cair
- Logs persistentes

✅ **Serviço Cloudflare Tunnel** (`cloudflared-tunnel.service`)
- Inicia automaticamente após o Flask
- Reinicia automaticamente se cair
- Logs persistentes

---

## 📋 Pré-requisitos

- Backend já instalado em `~/ccr-backend`
- Ambiente virtual Python em `~/ccr-backend/venv`
- Cloudflared instalado
- Permissões sudo

---

## 🚀 Instalação (Método Automático)

### 1. Enviar Arquivos para VM

**Do seu PC (PowerShell):**

```powershell
# Enviar arquivos de serviço
scp "D:\Users\rafa2\OneDrive\Desktop\monitoramento_vaga\parking-api.service" rafaelsantis@35.198.44.137:~/ccr-backend/
scp "D:\Users\rafa2\OneDrive\Desktop\monitoramento_vaga\cloudflared-tunnel.service" rafaelsantis@35.198.44.137:~/ccr-backend/
scp "D:\Users\rafa2\OneDrive\Desktop\monitoramento_vaga\setup-services.sh" rafaelsantis@35.198.44.137:~/ccr-backend/
```

### 2. Executar Instalação na VM

**Na VM do GCP:**

```bash
cd ~/ccr-backend

# Dar permissão de execução
chmod +x setup-services.sh

# Executar instalação
./setup-services.sh
```

---

## 🔧 Instalação (Método Manual)

### 1. Parar Processos Existentes

```bash
pkill -f api_server.py
pkill -f cloudflared
```

### 2. Copiar Arquivos de Serviço

```bash
cd ~/ccr-backend
sudo cp parking-api.service /etc/systemd/system/
sudo cp cloudflared-tunnel.service /etc/systemd/system/
```

### 3. Habilitar Serviços

```bash
sudo systemctl daemon-reload
sudo systemctl enable parking-api.service
sudo systemctl enable cloudflared-tunnel.service
```

### 4. Iniciar Serviços

```bash
sudo systemctl start parking-api.service
sudo systemctl start cloudflared-tunnel.service
```

---

## 📊 Comandos Úteis

### Verificar Status

```bash
# Status do Flask
sudo systemctl status parking-api.service

# Status do Cloudflare
sudo systemctl status cloudflared-tunnel.service

# Status de ambos
sudo systemctl status parking-api.service cloudflared-tunnel.service
```

### Ver Logs em Tempo Real

```bash
# Logs do Flask
sudo journalctl -u parking-api.service -f

# Logs do Cloudflare
sudo journalctl -u cloudflared-tunnel.service -f

# Logs de ambos
sudo journalctl -u parking-api.service -u cloudflared-tunnel.service -f
```

### Controlar Serviços

```bash
# Reiniciar Flask
sudo systemctl restart parking-api.service

# Reiniciar Cloudflare
sudo systemctl restart cloudflared-tunnel.service

# Parar tudo
sudo systemctl stop parking-api.service cloudflared-tunnel.service

# Iniciar tudo
sudo systemctl start parking-api.service cloudflared-tunnel.service
```

### Desabilitar Auto-Start

```bash
sudo systemctl disable parking-api.service
sudo systemctl disable cloudflared-tunnel.service
```

---

## 🧪 Testar Resiliência

### Teste 1: Matar Processo Flask

```bash
# Pegar PID do Flask
ps aux | grep api_server.py

# Matar processo
sudo kill -9 <PID>

# Verificar se reiniciou automaticamente (aguarde 10 segundos)
sudo systemctl status parking-api.service
```

**Deve mostrar:** "Active: active (running)"

### Teste 2: Matar Cloudflare Tunnel

```bash
# Pegar PID do cloudflared
ps aux | grep cloudflared

# Matar processo
sudo kill -9 <PID>

# Verificar se reiniciou automaticamente (aguarde 10 segundos)
sudo systemctl status cloudflared-tunnel.service
```

**Deve mostrar:** "Active: active (running)"

### Teste 3: Reiniciar VM

```bash
sudo reboot
```

Aguarde 2-3 minutos e verifique se os serviços iniciaram automaticamente:

```bash
sudo systemctl status parking-api.service cloudflared-tunnel.service
```

---

## 🌐 Obter URL do Cloudflare Tunnel

```bash
# Método 1: Ver logs
tail -50 ~/ccr-backend/cloudflared.log | grep trycloudflare

# Método 2: Journalctl
sudo journalctl -u cloudflared-tunnel.service | grep trycloudflare | tail -1
```

⚠️ **IMPORTANTE:** Se reiniciar o Cloudflare Tunnel, a URL muda! Atualize:
1. `.env` no backend (variável `STREAM_BASE_URL`)
2. Vercel (variável `VITE_API_URL`)

---

## 🔐 Segurança

### Permissões dos Arquivos

```bash
# Verificar permissões
ls -la /etc/systemd/system/parking-api.service
ls -la /etc/systemd/system/cloudflared-tunnel.service

# Devem ter: -rw-r--r-- root root
```

### Logs

Os logs ficam em:
- `/home/rafaelsantis/ccr-backend/api.log`
- `/home/rafaelsantis/ccr-backend/cloudflared.log`

Para limpar logs antigos:
```bash
> ~/ccr-backend/api.log
> ~/ccr-backend/cloudflared.log
```

---

## ⚡ Performance

### Verificar Uso de Recursos

```bash
# CPU e memória dos serviços
systemctl status parking-api.service
systemctl status cloudflared-tunnel.service

# Detalhes
top -p $(pgrep -f api_server.py)
top -p $(pgrep cloudflared)
```

### GPU

```bash
# Monitorar uso da GPU
nvidia-smi -l 1
```

---

## 🐛 Troubleshooting

### Serviço Não Inicia

```bash
# Ver logs detalhados
sudo journalctl -u parking-api.service -n 50 --no-pager

# Ver erros
sudo journalctl -u parking-api.service -p err -n 50
```

### Serviço Fica Reiniciando

```bash
# Ver histórico de restarts
sudo journalctl -u parking-api.service | grep "Started\|Stopped"

# Verificar arquivo .env
cat ~/ccr-backend/.env

# Verificar permissões
ls -la ~/ccr-backend/
```

### Cloudflare URL Mudou

```bash
# Reiniciar serviço para gerar nova URL
sudo systemctl restart cloudflared-tunnel.service

# Aguardar 10 segundos
sleep 10

# Ver nova URL
sudo journalctl -u cloudflared-tunnel.service -n 30 | grep trycloudflare

# Atualizar .env
nano ~/ccr-backend/.env
# Mudar STREAM_BASE_URL=<nova-url>

# Reiniciar Flask
sudo systemctl restart parking-api.service
```

---

## 📈 Monitoramento

### Script de Monitoramento Simples

Criar arquivo `monitor.sh`:

```bash
#!/bin/bash
while true; do
  clear
  echo "=== Status dos Serviços ==="
  sudo systemctl is-active parking-api.service
  sudo systemctl is-active cloudflared-tunnel.service
  echo ""
  echo "=== Uso de GPU ==="
  nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
  echo ""
  sleep 5
done
```

Executar:
```bash
chmod +x monitor.sh
./monitor.sh
```

---

## ✅ Checklist de Verificação

Após instalação, verifique:

- [ ] `sudo systemctl status parking-api.service` → Active (running)
- [ ] `sudo systemctl status cloudflared-tunnel.service` → Active (running)
- [ ] `sudo systemctl is-enabled parking-api.service` → enabled
- [ ] `sudo systemctl is-enabled cloudflared-tunnel.service` → enabled
- [ ] Logs sem erros críticos
- [ ] URL do Cloudflare Tunnel acessível
- [ ] Endpoint `/api/cameras` retornando câmeras
- [ ] GPU sendo utilizada (nvidia-smi)

---

## 📞 Suporte

Se algo der errado:

1. Verificar logs: `sudo journalctl -u parking-api.service -n 100`
2. Verificar status: `sudo systemctl status parking-api.service`
3. Verificar conectividade: `curl http://localhost:5000/api/cameras`
4. Verificar GPU: `nvidia-smi`

---

**Última Atualização:** 2025-10-29
**Versão:** 1.0
