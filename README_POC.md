# POC - Sistema de Monitoramento de Vagas de Estacionamento

Sistema completo para monitorar vagas de estacionamento em tempo real usando detecção por IA (YOLO11).

## 🚀 Início Rápido

### Backend (Python)

```bash
# Ativar ambiente virtual
venv\Scripts\activate

# Instalar dependências (se necessário)
pip install -r requirements.txt

# Iniciar servidor API
python api_server.py
```

O backend estará rodando em: `http://localhost:5000`

### Frontend (React)

```bash
cd frontend

# Instalar dependências (primeira vez)
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

O frontend estará rodando em: `http://localhost:5173`

## 📋 Fluxo de Uso

### 1. Adicionar Câmera
- Acesse: **Configuração** no menu lateral
- Clique em **"Adicionar Câmera"**
- Preencha:
  - Nome da câmera (ex: "Câmera 01")
  - Localização (ex: "Entrada Principal")
  - URL (RTSP ou HTTP): `rtsp://usuario:senha@ip:porta/path`

### 2. Configurar Áreas de Vagas
- Na lista de câmeras, clique em **"Configurar Vagas"**
- Um snapshot da câmera será carregado
- Clique em **4 pontos** para formar cada vaga (polígono)
- Clique em **"Confirmar Vaga"** após marcar os 4 pontos
- Repita para todas as vagas
- Clique em **"Salvar Todas"** quando terminar

### 3. Iniciar Monitoramento
- Volte para **Configuração**
- Clique em **"Iniciar"** na câmera desejada
- O backend começará a processar o stream

### 4. Visualizar no Videowall
- Acesse **Videowall** no menu lateral
- Visualize todas as câmeras ativas
- Veja o contador de vagas em tempo real
- Stats globais no painel lateral

## 🛠️ Tecnologias

### Backend
- **Python 3.10+**
- **Flask** - API REST
- **YOLO11** - Detecção de objetos
- **OpenCV** - Processamento de vídeo
- **Threading** - Múltiplas câmeras simultâneas

### Frontend
- **React 18** + **TypeScript**
- **Vite** - Build tool
- **TailwindCSS** - Estilização
- **React Router** - Navegação

## 📁 Estrutura de Arquivos

```
monitoramento_vaga/
├── api_server.py          # Backend API principal
├── capture.py             # Classe de captura de vídeo
├── inferencia.py          # Backend legado (backup)
├── desenho.py             # Tool para desenhar áreas (desktop)
├── cameras_config.json    # Config das câmeras (gerado automaticamente)
├── parking_areas.json     # Áreas de vagas (legado)
├── requirements.txt       # Dependências Python
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Videowall.tsx       # Página principal de monitoramento
    │   │   ├── CameraConfig.tsx    # Gerenciamento de câmeras
    │   │   ├── CameraAreas.tsx     # Desenhar áreas de vagas
    │   │   └── Dashboard.tsx
    │   └── components/
    │       ├── Layout.tsx
    │       └── Sidebar.tsx
    └── package.json
```

## 🔧 API Endpoints

### Câmeras
- `GET /api/cameras` - Lista todas as câmeras
- `POST /api/cameras` - Adiciona nova câmera
- `DELETE /api/cameras/<id>` - Remove câmera
- `POST /api/cameras/<id>/start` - Inicia processamento
- `POST /api/cameras/<id>/stop` - Para processamento

### Áreas
- `GET /api/cameras/<id>/snapshot` - Captura frame para desenhar
- `POST /api/cameras/<id>/areas` - Salva áreas desenhadas

### Stream
- `GET /api/cameras/<id>/stream` - Stream de vídeo processado (MJPEG)
- `GET /api/cameras/<id>/status` - Status das vagas em tempo real

## 💡 Dicas

1. **URLs de Câmera**:
   - RTSP: `rtsp://admin:senha@192.168.1.100:554/stream`
   - HTTP: `http://192.168.1.100:8080/video`

2. **Performance**:
   - Recomendado até 4 câmeras simultâneas
   - Use resolução 1280x720 para melhor performance

3. **Desenho de Áreas**:
   - Marque os 4 cantos da vaga em sentido horário
   - Para vagas diagonais, siga a mesma lógica

4. **Troubleshooting**:
   - Se o stream não carregar, verifique a URL da câmera
   - Se a detecção não funcionar, verifique se as áreas foram salvas
   - Backend e frontend devem rodar simultaneamente

## 📊 Limites da POC

- Máximo de 4 câmeras recomendado
- Detecção baseada em centroide (centro do veículo deve estar dentro da área)
- Não persiste histórico (apenas tempo real)
- Autenticação básica (sem backend real)

## 🎯 Próximos Passos (Pós-POC)

- [ ] Autenticação real com banco de dados
- [ ] Histórico de ocupação
- [ ] Notificações e alertas
- [ ] Suporte para mais câmeras
- [ ] Detecção mais precisa (IoU baseada)
- [ ] Deploy em produção
