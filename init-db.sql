-- init-db.sql
-- Этот скрипт автоматически выполнится при первом запуске контейнера с БД
-- Создаем таблицу для хранения прогнозов

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    match_time TIMESTAMP NOT NULL,
    prediction_type VARCHAR(50) NOT NULL DEFAULT 'btts',
    prediction_value VARCHAR(50) NOT NULL, -- Может быть 'Yes', 'No' или коэффициент
    source VARCHAR(100) NOT NULL DEFAULT 'scores24.live',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Создаем индекс для быстрого поиска по командам и времени
    UNIQUE (home_team, away_team, match_time, prediction_type)
);

-- Создаем таблицу для хранения результатов матчей
CREATE TABLE IF NOT EXISTS results (
    id SERIAL PRIMARY KEY,
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    match_time TIMESTAMP NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    status VARCHAR(50) DEFAULT 'Scheduled',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (home_team, away_team, match_time)
);

-- Создаем таблицу для анализа точности прогнозов
CREATE TABLE IF NOT EXISTS analysis (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER REFERENCES predictions(id) ON DELETE CASCADE,
    result_id INTEGER REFERENCES results(id) ON DELETE CASCADE,
    is_correct BOOLEAN,
    analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Создаем индекс для быстрого поиска прогнозов, которые еще не были проверены
CREATE INDEX IF NOT EXISTS idx_predictions_for_analysis ON predictions (match_time) 
WHERE match_time < NOW() - INTERVAL '3 hours'; -- Матчи, которые завершились более 3 часов назад

-- Комментарий к таблицам
COMMENT ON TABLE predictions IS 'Таблица для хранения спарсенных прогнозов на матчи';
COMMENT ON TABLE results IS 'Таблица для хранения реальных результатов матчей';
COMMENT ON TABLE analysis IS 'Таблица для связи прогнозов и результатов, хранит точность прогноза';
