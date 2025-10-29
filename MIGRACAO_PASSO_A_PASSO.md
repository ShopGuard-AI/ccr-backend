# 🚀 Migração de Dados JSON → Supabase

## Passo a Passo Completo

### 1️⃣ Criar as Tabelas (Se ainda não criou)

Primeiro, execute o schema no Supabase:

1. Acesse: https://supabase.com/dashboard/project/rvfrxbcirqonkzfbpyfh
2. Vá em **SQL Editor** → **New Query**
3. Abra o arquivo `supabase_schema.sql`
4. **Copie TODO o conteúdo** e cole no editor
5. Clique em **Run**

✅ Aguarde a mensagem de sucesso!

---

### 2️⃣ Migrar os Dados do JSON

Agora vamos migrar os dados das 2 câmeras:

1. No mesmo **SQL Editor** do Supabase
2. Clique em **New Query** novamente
3. Abra o arquivo `migrate_json_to_supabase.sql`
4. **Copie TODO o conteúdo** e cole no editor
5. Clique em **Run**

✅ Você verá os resultados da verificação no final!

---

### 3️⃣ Verificar se Funcionou

Após executar, você verá automaticamente 3 queries de verificação:

#### ✓ Câmeras inseridas:
```
id                | name | location              | status | areas_count
1761547959251     | cam1 | estacionamento1-gcs   | online | 3
1761548907838     | cam2 | estacionamento2       | online | 3
```

#### ✓ Áreas de estacionamento:
```
6 áreas inseridas (3 para cada câmera)
```

#### ✓ Eventos registrados:
```
6 eventos (criação, configuração de áreas, camera online)
```

---

### 4️⃣ Verificar na Interface Web

1. Abra a aplicação: http://localhost:5173
2. Vá em **Videowall**
3. Você verá as 2 câmeras aparecendo!

---

## 🔄 O que o Script Faz

### Dados Migrados:

**Câmera 1:**
- ID: `1761547959251`
- Nome: `cam1`
- Localização: `estacionamento1-gcs`
- URL: `rtsp://admin:Gcs@9282@192.168.1.254:554/Streaming/Channels/101`
- Status: `online`
- **3 áreas** configuradas (polígonos com 4 pontos cada)

**Câmera 2:**
- ID: `1761548907838`
- Nome: `cam2`
- Localização: `estacionamento2`
- URL: `rtsp://admin:Gcs@9282@192.168.1.254:554/Streaming/Channels/201`
- Status: `online`
- **3 áreas** configuradas (polígonos com 4 pontos cada)

### Eventos Criados:

Para cada câmera:
- ✓ `camera_created` - Registro de criação
- ✓ `areas_configured` - Registro de configuração das áreas
- ✓ `camera_online` - Registro de câmera ativa

---

## ⚠️ IMPORTANTE

### Se Executar Múltiplas Vezes:
O script usa `ON CONFLICT` e `DELETE` antes de inserir, então é **seguro executar múltiplas vezes**.

### Se Quiser Limpar Tudo:
Descomente a primeira linha do script:
```sql
DELETE FROM cameras;  -- Remove TUDO (usa CASCADE)
```

---

## 🎯 Próximos Passos

Após a migração:

1. ✅ Dados já estão no Supabase
2. ✅ Backend vai salvar histórico automaticamente (a cada 60s)
3. ✅ Todas as mudanças serão persistidas no banco
4. ✅ Você pode consultar histórico, eventos e estatísticas

### Consultar Dados Pelo Backend:

```bash
# Histórico de ocupação das últimas 24h
curl http://localhost:5000/api/cameras/1761547959251/history?hours=24

# Eventos da câmera
curl http://localhost:5000/api/cameras/1761547959251/events?limit=50

# Stats em tempo real
curl http://localhost:5000/api/realtime-stats
```

---

## ✨ Tudo Pronto!

Seus dados foram migrados e o sistema está **100% integrado** com o Supabase! 🎉
