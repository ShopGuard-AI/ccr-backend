-- Schema para o banco de dados Supabase
-- Execute este script no SQL Editor do Supabase

-- 1. Tabela de Câmeras
CREATE TABLE IF NOT EXISTS cameras (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT DEFAULT 'offline',
    areas_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Tabela de Áreas de Estacionamento
CREATE TABLE IF NOT EXISTS parking_areas (
    id SERIAL PRIMARY KEY,
    camera_id TEXT REFERENCES cameras(id) ON DELETE CASCADE,
    area_index INTEGER NOT NULL,
    points JSONB NOT NULL, -- Array de pontos [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(camera_id, area_index)
);

-- 3. Tabela de Histórico de Ocupação
CREATE TABLE IF NOT EXISTS occupancy_history (
    id SERIAL PRIMARY KEY,
    camera_id TEXT REFERENCES cameras(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_spots INTEGER NOT NULL,
    occupied_spots INTEGER NOT NULL,
    free_spots INTEGER NOT NULL,
    occupancy_percentage NUMERIC(5,2) NOT NULL,
    fps NUMERIC(5,2),
    details JSONB -- Detalhes adicionais como status de cada vaga
);

-- 4. Tabela de Estatísticas Diárias
CREATE TABLE IF NOT EXISTS daily_statistics (
    id SERIAL PRIMARY KEY,
    camera_id TEXT REFERENCES cameras(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    avg_occupancy NUMERIC(5,2),
    max_occupancy NUMERIC(5,2),
    min_occupancy NUMERIC(5,2),
    total_entries INTEGER DEFAULT 0,
    peak_hour INTEGER, -- Hora do pico (0-23)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(camera_id, date)
);

-- 5. Tabela de Eventos
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    camera_id TEXT REFERENCES cameras(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, -- 'camera_online', 'camera_offline', 'critical_occupancy', etc
    description TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- Índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_occupancy_camera_timestamp ON occupancy_history(camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_camera_timestamp ON events(camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_daily_stats_camera_date ON daily_statistics(camera_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para atualizar updated_at na tabela cameras
DROP TRIGGER IF EXISTS update_cameras_updated_at ON cameras;
CREATE TRIGGER update_cameras_updated_at
    BEFORE UPDATE ON cameras
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Políticas RLS (Row Level Security) - Opcional
-- ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE parking_areas ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE occupancy_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE daily_statistics ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Política de exemplo (ajuste conforme sua necessidade)
-- CREATE POLICY "Enable read access for all users" ON cameras FOR SELECT USING (true);
-- CREATE POLICY "Enable insert for authenticated users only" ON cameras FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Views úteis

-- View de estatísticas em tempo real por câmera
CREATE OR REPLACE VIEW camera_stats_realtime AS
SELECT
    c.id,
    c.name,
    c.location,
    c.status,
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

-- View de ocupação por hora
CREATE OR REPLACE VIEW hourly_occupancy AS
SELECT
    camera_id,
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(occupancy_percentage) as avg_occupancy,
    MAX(occupied_spots) as max_occupied,
    MIN(free_spots) as min_free,
    COUNT(*) as readings
FROM occupancy_history
GROUP BY camera_id, DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;

-- Comentários nas tabelas
COMMENT ON TABLE cameras IS 'Informações das câmeras de monitoramento';
COMMENT ON TABLE parking_areas IS 'Áreas de vagas configuradas para cada câmera';
COMMENT ON TABLE occupancy_history IS 'Histórico de ocupação das vagas em tempo real';
COMMENT ON TABLE daily_statistics IS 'Estatísticas agregadas diárias';
COMMENT ON TABLE events IS 'Log de eventos do sistema';

-- Dados iniciais de exemplo (opcional)
-- INSERT INTO cameras (id, name, location, url, status)
-- VALUES ('demo-cam-1', 'Câmera Demo', 'Estacionamento Principal', 'rtsp://demo', 'online')
-- ON CONFLICT (id) DO NOTHING;
