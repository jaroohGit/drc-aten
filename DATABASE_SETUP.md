# TimescaleDB Setup Guide for DRC Online

## Prerequisites

1. **Install PostgreSQL 14 or later**
   - Download from: https://www.postgresql.org/download/windows/
   - During installation, remember your postgres password

2. **Install TimescaleDB Extension**
   - Download from: https://www.timescale.com/download
   - Or use: `choco install timescaledb` (if you have Chocolatey)

## Quick Setup

### Option 1: Automatic Setup (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the setup script with psql
psql -U postgres -f setup_timescaledb.sql
```

### Option 2: Manual Setup

1. **Open PostgreSQL Command Line (psql)**
```bash
psql -U postgres
```

2. **Create Database**
```sql
CREATE DATABASE nanovna_db;
\c nanovna_db
```

3. **Enable TimescaleDB**
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

4. **Run the setup script**
```bash
\i setup_timescaledb.sql
```

## Configuration

### Environment Variables (Optional)

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nanovna_db
DB_USER=postgres
DB_PASSWORD=your_password_here
```

Or set them in your system:

```bash
# Windows PowerShell
$env:DB_HOST="localhost"
$env:DB_PASSWORD="your_password"

# Windows CMD
set DB_HOST=localhost
set DB_PASSWORD=your_password
```

### Default Configuration

If no environment variables are set, the application uses:
- Host: `localhost`
- Port: `5432`
- Database: `nanovna_db`
- User: `postgres`
- Password: `postgres`

## Verify Installation

1. **Check TimescaleDB Version**
```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';
```

2. **Check Tables**
```sql
\c nanovna_db
\dt
```

You should see:
- `measurements` (hypertable)
- `measurement_summary`

## Using the Application

1. **Start the application**
```bash
python app.py
```

2. **Look for this message:**
```
✓ Database initialized successfully
✓ Database ready
```

3. **Save measurements:**
   - Click "💾 Save Data" button in the header
   - Check "Last Saved" timestamp

## Troubleshooting

### Connection Error
```
✗ Database initialization error: connection failed
```

**Solutions:**
1. Check PostgreSQL is running: `services.msc` (Windows) → PostgreSQL service
2. Verify password: `psql -U postgres`
3. Check firewall: port 5432 should be open

### Extension Not Found
```
ERROR: could not open extension control file
```

**Solution:**
Install TimescaleDB extension:
```bash
# Windows
choco install timescaledb

# Or download from: https://www.timescale.com/download
```

### Running Without Database

If database is not available, the application will still run but data won't be saved:
```
⚠ Running without database (data will not be saved)
```

## Query Examples

### Get Last 100 Measurements
```sql
SELECT time, sweep_count, s11_rms, s21_rms 
FROM measurement_summary 
ORDER BY time DESC 
LIMIT 100;
```

### Get Average S11 by Hour
```sql
SELECT 
    time_bucket('1 hour', time) AS hour,
    AVG(s11_rms) as avg_s11,
    AVG(s21_rms) as avg_s21
FROM measurement_summary
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

### Get Frequency Response at Specific Time
```sql
SELECT frequency, s11_db, s21_db
FROM measurements
WHERE time = (SELECT MAX(time) FROM measurements)
ORDER BY frequency;
```

## Backup and Restore

### Backup
```bash
pg_dump -U postgres nanovna_db > backup.sql
```

### Restore
```bash
psql -U postgres nanovna_db < backup.sql
```

## Resources

- TimescaleDB Docs: https://docs.timescale.com/
- PostgreSQL Docs: https://www.postgresql.org/docs/
- psycopg2 Docs: https://www.psycopg.org/docs/
