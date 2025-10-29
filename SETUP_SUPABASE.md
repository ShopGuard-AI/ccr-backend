# Setup do Supabase - Guia Rápido

## Status da Conexão
✓ **Conexão estabelecida com sucesso!**
✓ **Credenciais configuradas corretamente**

## Próximo Passo: Criar Tabelas no Banco de Dados

### 1. Acesse o Supabase Dashboard
Abra no navegador: https://supabase.com/dashboard/project/rvfrxbcirqonkzfbpyfh

### 2. Abra o SQL Editor
- No menu lateral esquerdo, clique em **"SQL Editor"**
- Clique em **"New Query"** (botão no canto superior direito)

### 3. Execute o Schema SQL
1. Abra o arquivo `supabase_schema.sql` nesta pasta
2. **Copie TODO o conteúdo** do arquivo
3. **Cole** no SQL Editor do Supabase
4. Clique no botão **"Run"** (ou pressione Ctrl+Enter)

### 4. Verifique a Criação
Você deverá ver a mensagem de sucesso no Supabase indicando que as tabelas foram criadas.

As seguintes tabelas serão criadas:
- ✓ `cameras` - Informações das câmeras
- ✓ `parking_areas` - Áreas de estacionamento configuradas
- ✓ `occupancy_history` - Histórico de ocupação em tempo real
- ✓ `daily_statistics` - Estatísticas agregadas diárias
- ✓ `events` - Log de eventos do sistema

### 5. Teste Novamente
Após executar o SQL, rode o teste novamente:
```bash
python test_supabase.py
```

## O que o Sistema Salva Automaticamente

### Ao adicionar uma câmera:
- Configurações básicas (nome, localização, URL)
- Status (online/offline)
- Evento de criação

### Ao configurar áreas:
- Coordenadas dos polígonos de cada vaga
- Quantidade de vagas
- Evento de configuração

### Durante o monitoramento:
- **A cada 60 segundos**: snapshot da ocupação atual
  - Total de vagas
  - Vagas ocupadas
  - Vagas livres
  - Porcentagem de ocupação
  - FPS do processamento
- Eventos de câmera online/offline
- Eventos de erro (se houver)

## Endpoints Disponíveis para Consulta de Dados

### Histórico de Ocupação
```
GET /api/cameras/{camera_id}/history?hours=24
```
Retorna histórico de ocupação das últimas N horas (padrão: 24h)

### Eventos da Câmera
```
GET /api/cameras/{camera_id}/events?limit=50
```
Retorna eventos da câmera (padrão: 50 mais recentes)

### Estatísticas Diárias
```
GET /api/cameras/{camera_id}/statistics?days=7
```
Retorna estatísticas agregadas dos últimos N dias (padrão: 7 dias)

### Estatísticas em Tempo Real (Todas as Câmeras)
```
GET /api/realtime-stats
```
Retorna estatísticas atuais de todas as câmeras

## Estrutura do Banco

```
cameras (tabela principal)
  ├── id (TEXT PRIMARY KEY)
  ├── name, location, url
  ├── status (online/offline)
  └── areas_count

parking_areas (áreas de cada câmera)
  ├── id (SERIAL)
  ├── camera_id (FK → cameras)
  ├── area_index
  └── points (JSONB array de coordenadas)

occupancy_history (histórico em tempo real)
  ├── id (SERIAL)
  ├── camera_id (FK → cameras)
  ├── timestamp
  ├── total_spots, occupied_spots, free_spots
  ├── occupancy_percentage
  └── fps

daily_statistics (agregado diário)
  ├── id (SERIAL)
  ├── camera_id (FK → cameras)
  ├── date
  ├── avg_occupancy, max_occupancy, min_occupancy
  └── peak_hour

events (log de eventos)
  ├── id (SERIAL)
  ├── camera_id (FK → cameras)
  ├── event_type (camera_online, camera_offline, etc)
  ├── description
  └── timestamp
```

## Troubleshooting

### "Could not find table" - Execute o schema SQL no Supabase
### "Connection refused" - Verifique credenciais no arquivo .env
### "Invalid API key" - Regenere a chave no Supabase Dashboard

---
**Pronto!** Após executar o schema, seu sistema estará 100% integrado com o Supabase.
