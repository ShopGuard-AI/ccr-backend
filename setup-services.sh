#!/bin/bash
# Script para configurar serviços systemd para o backend

set -e

echo "🚀 Configurando serviços systemd..."

# Parar processos existentes
echo "⏹️  Parando processos existentes..."
pkill -f api_server.py || true
pkill -f cloudflared || true
sleep 2

# Copiar arquivos de serviço
echo "📋 Copiando arquivos de serviço..."
sudo cp parking-api.service /etc/systemd/system/
sudo cp cloudflared-tunnel.service /etc/systemd/system/

# Recarregar systemd
echo "🔄 Recarregando systemd..."
sudo systemctl daemon-reload

# Habilitar serviços para iniciar no boot
echo "✅ Habilitando auto-start..."
sudo systemctl enable parking-api.service
sudo systemctl enable cloudflared-tunnel.service

# Iniciar serviços
echo "▶️  Iniciando serviços..."
sudo systemctl start parking-api.service
sleep 5
sudo systemctl start cloudflared-tunnel.service
sleep 3

# Verificar status
echo ""
echo "📊 Status dos Serviços:"
echo "======================"
sudo systemctl status parking-api.service --no-pager | head -20
echo ""
sudo systemctl status cloudflared-tunnel.service --no-pager | head -20

echo ""
echo "✅ Configuração concluída!"
echo ""
echo "📝 Comandos úteis:"
echo "  - Ver logs do Flask:     sudo journalctl -u parking-api.service -f"
echo "  - Ver logs do Cloudflare: sudo journalctl -u cloudflared-tunnel.service -f"
echo "  - Reiniciar Flask:       sudo systemctl restart parking-api.service"
echo "  - Reiniciar Cloudflare:  sudo systemctl restart cloudflared-tunnel.service"
echo "  - Parar tudo:            sudo systemctl stop parking-api.service cloudflared-tunnel.service"
echo "  - Ver status:            sudo systemctl status parking-api.service"
echo ""
echo "🌐 URL do Cloudflare Tunnel:"
tail -30 ~/ccr-backend/cloudflared.log | grep -i "trycloudflare.com" | tail -1
