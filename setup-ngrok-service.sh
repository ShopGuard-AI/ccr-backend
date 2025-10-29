#!/bin/bash
# Script para configurar serviço systemd do ngrok

set -e

echo "🚀 Configurando serviço ngrok..."

# Parar processo ngrok existente
echo "⏹️  Parando processos ngrok existentes..."
pkill -f ngrok || true
sleep 2

# Copiar arquivo de serviço
echo "📋 Copiando arquivo de serviço..."
sudo cp ngrok-tunnel.service /etc/systemd/system/

# Recarregar systemd
echo "🔄 Recarregando systemd..."
sudo systemctl daemon-reload

# Habilitar serviço para iniciar no boot
echo "✅ Habilitando auto-start..."
sudo systemctl enable ngrok-tunnel.service

# Iniciar serviço
echo "▶️  Iniciando serviço ngrok..."
sudo systemctl start ngrok-tunnel.service
sleep 5

# Verificar status
echo ""
echo "📊 Status do Serviço ngrok:"
echo "======================="
sudo systemctl status ngrok-tunnel.service --no-pager | head -20

echo ""
echo "✅ Configuração concluída!"
echo ""
echo "📝 Comandos úteis:"
echo "  - Ver logs:           sudo journalctl -u ngrok-tunnel.service -f"
echo "  - Ver URL:            sudo journalctl -u ngrok-tunnel.service | grep 'url=' | tail -1"
echo "  - Reiniciar:          sudo systemctl restart ngrok-tunnel.service"
echo "  - Parar:              sudo systemctl stop ngrok-tunnel.service"
echo "  - Ver status:         sudo systemctl status ngrok-tunnel.service"
echo ""
echo "⚠️  IMPORTANTE: Após reiniciar o ngrok, a URL muda!"
echo "    Você precisará atualizar .env e Vercel com a nova URL."
