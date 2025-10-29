# 🚀 Auto-Start de Câmeras

## Problema Resolvido

Antes, as câmeras configuradas **NÃO iniciavam automaticamente** quando o servidor era iniciado, mesmo com `status: "online"` no JSON.

Isso causava:
- ❌ Streams vazios em `http://localhost:5000/api/cameras/{id}/stream`
- ❌ Stats vazios `{}`
- ❌ Necessidade de iniciar manualmente cada câmera

## Solução Implementada

### 1. Auto-Start no Startup

Adicionado função `auto_start_online_cameras()` que:
- ✅ Carrega configuração do JSON
- ✅ Identifica câmeras com `status: "online"` e áreas configuradas
- ✅ Inicia captura RTSP automaticamente
- ✅ Inicia thread de processamento YOLO
- ✅ Roda em background (não bloqueia startup do servidor)

### 2. Tratamento de Erros YOLO

Adicionado try-catch no processamento YOLO:
- ✅ Se YOLO falhar, continua processando sem detecção
- ✅ Frame é exibido mesmo sem detecções
- ✅ Stats de ocupação continuam funcionando
- ✅ Thread não morre por erro do modelo

## Como Usar

### Automático (Recomendado)

Simplesmente inicie o servidor:

```bash
cd venv/Scripts && activate && cd ../.. && python api_server.py
```

**Câmeras com `status: "online"` no JSON iniciarão automaticamente!**

### Manual (Se Necessário)

Pela interface web:
1. Vá em **Configuração**
2. Clique em **"Iniciar"** na câmera desejada

Ou via API:
```bash
curl -X POST http://localhost:5000/api/cameras/{camera_id}/start
```

## Verificar Status

### Via API:
```bash
curl http://localhost:5000/api/cameras
```

Procure por:
- `"status": "online"` - Câmera configurada como ativa
- `"stats": {...}` - Câmera REALMENTE processando (com FPS, vagas, etc)

Se `stats` está vazio `{}`, a câmera não está processando.

### Via Browser:
Acesse diretamente o stream:
```
http://localhost:5000/api/cameras/{camera_id}/stream
```

Você deve ver o vídeo com:
- ✅ Detecções de veículos (caixas coloridas)
- ✅ Áreas de estacionamento (polígonos verde/vermelho)
- ✅ FPS no canto superior esquerdo
- ✅ Labels nas vagas (#1 Livre, #2 Ocupada, etc)

## Logs

O servidor mostra logs claros:

```
INFO:__main__:Auto-starting camera 1761547959251 (cam1)
INFO:capture:Conexão estabelecida com sucesso.
INFO:__main__:Starting stream processing for camera 1761547959251
INFO:__main__:Camera 1761547959251 started successfully
```

Se houver erro:
```
ERROR:__main__:Failed to auto-start camera {id}: Connection timeout
```

## Requisitos

Para auto-start funcionar:
1. ✅ Câmera deve ter `"status": "online"` no JSON
2. ✅ Câmera deve ter áreas configuradas (`"areas": [...]`)
3. ✅ URL RTSP deve estar acessível

Se a URL não estiver acessível, a câmera será marcada como `"status": "offline"` automaticamente.

## Benefícios

- 🚀 **Zero configuração** - Funciona automaticamente
- 💾 **Persiste entre restarts** - Configuração salva no JSON
- 🔄 **Recuperação automática** - Reconecta se conexão cair
- 📊 **Dados históricos** - Salva no Supabase a cada 60s
- 🎯 **Pronto para produção** - Não requer intervenção manual

---

**Pronto para usar!** 🎉
