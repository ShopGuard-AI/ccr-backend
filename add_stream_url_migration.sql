-- Migração: Adicionar campo stream_url à tabela cameras
-- Execute este script no SQL Editor do Supabase

-- Adicionar coluna stream_url
ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS stream_url TEXT;

-- Adicionar comentário
COMMENT ON COLUMN cameras.stream_url IS 'URL pública do stream processado (ex: Cloudflare Tunnel URL)';

-- Deletar a view existente para recriar com a nova estrutura
DROP VIEW IF EXISTS camera_stats_realtime;

-- Recriar a view de estatísticas em tempo real incluindo stream_url
CREATE VIEW camera_stats_realtime AS
SELECT
    c.id,
    c.name,
    c.location,
    c.status,
    c.stream_url,
    c.areas_count,
    oh.occupied_spots,
    oh.free_spots,
    oh.total_spots,
    oh.occupancy_percentage,
    oh.fps,
    oh.timestamp as last_update
FROM cameras c
LEFT JOIN LATERAL (
    SELECT * FROM occupancy_history
    WHERE camera_id = c.id
    ORDER BY timestamp DESC
    LIMIT 1
) oh ON true;
