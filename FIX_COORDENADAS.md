# 🔧 Correção de Coordenadas das Áreas

## 🐛 Problema Original

As áreas desenhadas na interface de configuração não estavam alinhadas corretamente no stream processado.

### Causa Raiz:

**Inconsistência de dimensões** entre o snapshot e o processamento:

```
┌─────────────────────────────────────────┐
│ ANTES (INCORRETO)                       │
├─────────────────────────────────────────┤
│ 1. Snapshot para desenhar:              │
│    - Frame vem em qualquer tamanho      │
│    - Redimensionado para MAX_DISPLAY    │
│    - Usuário desenha coordenadas        │
│                                          │
│ 2. Processamento:                       │
│    - Frame pode vir em tamanho diferente│
│    - Aplica áreas direto (tamanho ≠)    │
│    - Redimensiona DEPOIS                │
│                                          │
│ ❌ Resultado: Áreas desalinhadas!       │
└─────────────────────────────────────────┘
```

## ✅ Solução Implementada

**Forçar tamanho consistente (1280x720) em TODOS os pontos:**

```
┌─────────────────────────────────────────┐
│ AGORA (CORRETO)                         │
├─────────────────────────────────────────┤
│ 1. Snapshot:                            │
│    - Força CAPTURE_WIDTH x HEIGHT       │
│    - cap.set(CAP_PROP_FRAME_WIDTH, 1280)│
│    - Garante resize se necessário       │
│    → Frame SEMPRE 1280x720              │
│                                          │
│ 2. Processamento:                       │
│    - Garante frame em 1280x720          │
│    - Aplica áreas (tamanho ==)          │
│    - Redimensiona DEPOIS para exibição  │
│                                          │
│ ✅ Resultado: Áreas perfeitamente       │
│    alinhadas!                           │
└─────────────────────────────────────────┘
```

## 📝 Mudanças no Código

### 1. Snapshot (`/api/cameras/<id>/snapshot`)

**ANTES:**
```python
cap = cv2.VideoCapture(video_url)
ret, frame = cap.read()
# Frame vem em qualquer tamanho
frame = resize_to_fit(frame)  # Pode não ser exato
```

**DEPOIS:**
```python
cap = cv2.VideoCapture(video_url)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)   # Força 1280
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT) # Força 720
ret, frame = cap.read()

# Garante tamanho exato
if frame.shape[1] != CAPTURE_WIDTH or frame.shape[0] != CAPTURE_HEIGHT:
    frame = cv2.resize(frame, (CAPTURE_WIDTH, CAPTURE_HEIGHT))
```

### 2. Processamento de Stream (`process_camera_stream`)

**ANTES:**
```python
grabbed, frame, status = cap.read()
# Frame pode variar de tamanho
# Processa direto com YOLO
```

**DEPOIS:**
```python
grabbed, frame, status = cap.read()

# Garante tamanho ANTES de processar
if frame.shape[1] != CAPTURE_WIDTH or frame.shape[0] != CAPTURE_HEIGHT:
    frame = cv2.resize(frame, (CAPTURE_WIDTH, CAPTURE_HEIGHT))

# Agora processa com YOLO
```

## 🎯 Dimensões Padrão

```python
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
```

**Todos os frames seguem estas dimensões até o último momento:**
1. ✅ Snapshot → 1280x720
2. ✅ Desenho de áreas → 1280x720
3. ✅ Processamento YOLO → 1280x720
4. ✅ Aplicação de áreas → 1280x720
5. ✅ Redimensionamento final → Apenas para exibição

## 📊 Fluxo Correto

```
Câmera RTSP
    ↓
VideoCapture (força 1280x720)
    ↓
┌─────────────┬──────────────┐
│   Snapshot  │ Processamento│
│             │              │
│ Força       │ Verifica e   │
│ 1280x720    │ garante      │
│             │ 1280x720     │
│      ↓      │      ↓       │
│  Frontend   │   YOLO +     │
│  desenha    │   Áreas      │
│  áreas      │   aplicadas  │
│      ↓      │      ↓       │
└─────┬───────┴──────┬───────┘
      │              │
      └──→ Mesmas ←──┘
         coordenadas!
              ↓
         Redimensiona
         para exibição
```

## 🚀 Como Testar

1. **Reinicie o servidor** para aplicar as mudanças:
   ```bash
   python api_server.py
   ```

2. **Adicione uma nova câmera** ou **reconfigure áreas existentes**:
   - Vá em Configuração
   - Clique "Configurar Áreas"
   - Desenhe as vagas
   - Salve

3. **Inicie a câmera** e vá para Videowall

4. **Verifique** se as áreas estão perfeitamente alinhadas!

## ⚠️ Importante

Se você já tinha áreas configuradas com as coordenadas antigas:
- **Reconfigure as áreas** após reiniciar o servidor
- As coordenadas antigas não serão válidas

## ✨ Resultado Esperado

✅ Áreas verdes/vermelhas exatamente onde você desenhou
✅ Detecção de ocupação precisa
✅ Polígonos perfeitamente alinhados com as vagas reais

---

**Problema resolvido!** 🎉
