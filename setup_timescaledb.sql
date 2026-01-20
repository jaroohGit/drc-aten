-- TimescaleDB Setup Script for NanoVNA DRC Online
-- Run this script to create the database and enable TimescaleDB extension

-- Create database
CREATE DATABASE nanovna_db;

-- Connect to the database
\c nanovna_db

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create measurements table
CREATE TABLE IF NOT EXISTS measurements (
    time TIMESTAMPTZ NOT NULL,
    sweep_count INTEGER,
    frequency DOUBLE PRECISION,
    s11_magnitude DOUBLE PRECISION,
    s11_db DOUBLE PRECISION,
    s11_phase DOUBLE PRECISION,
    s11_real DOUBLE PRECISION,
    s11_imag DOUBLE PRECISION,
    s21_magnitude DOUBLE PRECISION,
    s21_db DOUBLE PRECISION,
    s21_phase DOUBLE PRECISION,
    s21_real DOUBLE PRECISION,
    s21_imag DOUBLE PRECISION
);

-- Convert to hypertable
SELECT create_hypertable('measurements', 'time', if_not_exists => TRUE);

-- Create summary table
CREATE TABLE IF NOT EXISTS measurement_summary (
    time TIMESTAMPTZ NOT NULL PRIMARY KEY,
    sweep_count INTEGER,
    s11_rms DOUBLE PRECISION,
    s11_max DOUBLE PRECISION,
    s11_min DOUBLE PRECISION,
    s21_rms DOUBLE PRECISION,
    s21_max DOUBLE PRECISION,
    s21_min DOUBLE PRECISION,
    signal_quality DOUBLE PRECISION
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_measurements_sweep ON measurements (sweep_count, time DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_freq ON measurements (frequency, time DESC);
CREATE INDEX IF NOT EXISTS idx_summary_time ON measurement_summary (time DESC);

-- Grant permissions (adjust username as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;

-- Create DRC settings table
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

-- Create indexes for model tables
CREATE INDEX IF NOT EXISTS idx_trained_models_active ON trained_models (is_active);
CREATE INDEX IF NOT EXISTS idx_trained_models_created ON trained_models (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_dataset_timestamp ON training_dataset (timestamp DESC);

-- Display tables
\dt

-- Success message
SELECT 'TimescaleDB setup completed successfully!' AS status;
