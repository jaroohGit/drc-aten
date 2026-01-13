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

-- Display tables
\dt

-- Success message
SELECT 'TimescaleDB setup completed successfully!' AS status;
