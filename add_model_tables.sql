-- Add Model Training Tables to Existing Database
-- Run this to add model management tables without recreating the entire database

-- Connect to your database
\c nanovna_db

-- Create trained models table for ML model management
CREATE TABLE IF NOT EXISTS trained_models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    training_count INTEGER,
    rmse DOUBLE PRECISION,
    r_squared DOUBLE PRECISION,
    mae DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,
    notes TEXT
);

-- Create training dataset table
CREATE TABLE IF NOT EXISTS training_dataset (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50),
    weight_gross DOUBLE PRECISION,
    weight_net DOUBLE PRECISION,
    factor DOUBLE PRECISION,
    drc_evaluate DOUBLE PRECISION,
    drc_calculate DOUBLE PRECISION,
    s21_avg DOUBLE PRECISION,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create DRC settings table (if not exists)
CREATE TABLE IF NOT EXISTS drc_settings (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50),
    weight_gross DOUBLE PRECISION,
    weight_net DOUBLE PRECISION,
    factor DOUBLE PRECISION,
    drc_evaluate DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for model tables
CREATE INDEX IF NOT EXISTS idx_trained_models_active ON trained_models (is_active);
CREATE INDEX IF NOT EXISTS idx_trained_models_created ON trained_models (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_dataset_timestamp ON training_dataset (timestamp DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;

-- Display all tables
\dt

-- Success message
SELECT 'Model tables added successfully!' AS status;
