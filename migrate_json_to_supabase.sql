-- =========================================================
-- MIGRAÇÃO DE DADOS DO JSON PARA SUPABASE
-- Execute este script no SQL Editor do Supabase
-- =========================================================

-- Limpa dados existentes (CUIDADO: só execute se quiser começar do zero)
-- DELETE FROM cameras;  -- Isso também remove áreas, histórico e eventos por CASCADE

-- =========================================================
-- 1. INSERIR CÂMERAS
-- =========================================================

-- Câmera 1
INSERT INTO cameras (id, name, location, url, status, areas_count, created_at, updated_at)
VALUES (
    '1761547959251',
    'cam1',
    'estacionamento1-gcs',
    'rtsp://admin:Gcs@9282@192.168.1.254:554/Streaming/Channels/101',
    'online',
    3,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    location = EXCLUDED.location,
    url = EXCLUDED.url,
    status = EXCLUDED.status,
    areas_count = EXCLUDED.areas_count,
    updated_at = NOW();

-- Câmera 2
INSERT INTO cameras (id, name, location, url, status, areas_count, created_at, updated_at)
VALUES (
    '1761548907838',
    'cam2',
    'estacionamento2',
    'rtsp://admin:Gcs@9282@192.168.1.254:554/Streaming/Channels/201',
    'online',
    3,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    location = EXCLUDED.location,
    url = EXCLUDED.url,
    status = EXCLUDED.status,
    areas_count = EXCLUDED.areas_count,
    updated_at = NOW();

-- =========================================================
-- 2. INSERIR ÁREAS DE ESTACIONAMENTO - CÂMERA 1
-- =========================================================

-- Remove áreas existentes da câmera 1 (para evitar duplicação)
DELETE FROM parking_areas WHERE camera_id = '1761547959251';

-- Área 1 da Câmera 1
INSERT INTO parking_areas (camera_id, area_index, points, created_at)
VALUES (
    '1761547959251',
    0,
    '[[344, 217], [329, 374], [186, 378], [203, 219]]'::jsonb,
    NOW()
);

-- Área 2 da Câmera 1
INSERT INTO parking_areas (camera_id, area_index, points, created_at)
VALUES (
    '1761547959251',
    1,
    '[[26, 232], [11, 366], [154, 378], [145, 223]]'::jsonb,
    NOW()
);

-- Área 3 da Câmera 1
INSERT INTO parking_areas (camera_id, area_index, points, created_at)
VALUES (
    '1761547959251',
    2,
    '[[1043, 540], [705, 591], [645, 402], [927, 342]]'::jsonb,
    NOW()
);

-- =========================================================
-- 3. INSERIR ÁREAS DE ESTACIONAMENTO - CÂMERA 2
-- =========================================================

-- Remove áreas existentes da câmera 2 (para evitar duplicação)
DELETE FROM parking_areas WHERE camera_id = '1761548907838';

-- Área 1 da Câmera 2
INSERT INTO parking_areas (camera_id, area_index, points, created_at)
VALUES (
    '1761548907838',
    0,
    '[[77, 232], [120, 355], [261, 325], [188, 206]]'::jsonb,
    NOW()
);

-- Área 2 da Câmera 2
INSERT INTO parking_areas (camera_id, area_index, points, created_at)
VALUES (
    '1761548907838',
    1,
    '[[212, 202], [286, 308], [410, 264], [333, 176]]'::jsonb,
    NOW()
);

-- Área 3 da Câmera 2
INSERT INTO parking_areas (camera_id, area_index, points, created_at)
VALUES (
    '1761548907838',
    2,
    '[[455, 251], [545, 221], [419, 151], [363, 179]]'::jsonb,
    NOW()
);

-- =========================================================
-- 4. REGISTRAR EVENTOS DE MIGRAÇÃO
-- =========================================================

-- Evento de criação da Câmera 1
INSERT INTO events (camera_id, event_type, description, timestamp, metadata)
VALUES (
    '1761547959251',
    'camera_created',
    'Camera cam1 was created',
    NOW(),
    '{"source": "migration", "method": "manual_sql"}'::jsonb
);

-- Evento de configuração de áreas da Câmera 1
INSERT INTO events (camera_id, event_type, description, timestamp, metadata)
VALUES (
    '1761547959251',
    'areas_configured',
    '3 parking areas configured',
    NOW(),
    '{"source": "migration", "areas_count": 3}'::jsonb
);

-- Evento de câmera online da Câmera 1
INSERT INTO events (camera_id, event_type, description, timestamp, metadata)
VALUES (
    '1761547959251',
    'camera_online',
    'Camera started processing',
    NOW(),
    '{"source": "migration"}'::jsonb
);

-- Evento de criação da Câmera 2
INSERT INTO events (camera_id, event_type, description, timestamp, metadata)
VALUES (
    '1761548907838',
    'camera_created',
    'Camera cam2 was created',
    NOW(),
    '{"source": "migration", "method": "manual_sql"}'::jsonb
);

-- Evento de configuração de áreas da Câmera 2
INSERT INTO events (camera_id, event_type, description, timestamp, metadata)
VALUES (
    '1761548907838',
    'areas_configured',
    '3 parking areas configured',
    NOW(),
    '{"source": "migration", "areas_count": 3}'::jsonb
);

-- Evento de câmera online da Câmera 2
INSERT INTO events (camera_id, event_type, description, timestamp, metadata)
VALUES (
    '1761548907838',
    'camera_online',
    'Camera started processing',
    NOW(),
    '{"source": "migration"}'::jsonb
);

-- =========================================================
-- 5. VERIFICAÇÃO DOS DADOS INSERIDOS
-- =========================================================

-- Verifica câmeras
SELECT
    id,
    name,
    location,
    status,
    areas_count,
    created_at
FROM cameras
ORDER BY created_at;

-- Verifica áreas de estacionamento
SELECT
    camera_id,
    area_index,
    points,
    created_at
FROM parking_areas
ORDER BY camera_id, area_index;

-- Verifica eventos
SELECT
    camera_id,
    event_type,
    description,
    timestamp
FROM events
ORDER BY timestamp DESC
LIMIT 20;

-- Verifica estatísticas em tempo real (view)
SELECT * FROM camera_stats_realtime;

-- =========================================================
-- FIM DA MIGRAÇÃO
-- =========================================================

-- RESULTADO ESPERADO:
-- ✓ 2 câmeras inseridas
-- ✓ 6 áreas de estacionamento (3 por câmera)
-- ✓ 6 eventos registrados (3 por câmera)
-- ✓ Status: ambas câmeras online
-- ✓ Pronto para processar streams em tempo real!
