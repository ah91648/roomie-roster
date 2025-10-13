#!/bin/bash

# RoomieRoster Database Backup Script (Local Storage)
# This script creates a compressed backup of the PostgreSQL database
# and stores it locally in the backend/backups directory

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKUP_DIR="$SCRIPT_DIR/../backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/roomieroster_backup_$TIMESTAMP.sql"
COMPRESSED_FILE="$BACKUP_FILE.gz"
RETENTION_DAYS=30  # Keep backups for 30 days

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    # Try to load from .env file
    ENV_FILE="$SCRIPT_DIR/../../.env"
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | grep DATABASE_URL | xargs)
    fi

    if [ -z "$DATABASE_URL" ]; then
        error "DATABASE_URL not set. Please set it in .env or as environment variable."
        exit 1
    fi
fi

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    error "pg_dump not found. Please install PostgreSQL client tools:"
    echo "  macOS: brew install postgresql@15"
    echo "  Ubuntu: sudo apt-get install postgresql-client"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log "Starting database backup..."
log "Backup file: $COMPRESSED_FILE"

# Create the backup
if pg_dump "$DATABASE_URL" > "$BACKUP_FILE" 2>&1; then
    log "✅ Database dump created successfully"

    # Compress the backup
    if gzip "$BACKUP_FILE"; then
        log "✅ Backup compressed successfully"

        # Get file size
        SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        log "📦 Backup size: $SIZE"

        # Clean up old backups
        log "🧹 Cleaning up backups older than $RETENTION_DAYS days..."
        find "$BACKUP_DIR" -name "roomieroster_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

        BACKUP_COUNT=$(find "$BACKUP_DIR" -name "roomieroster_backup_*.sql.gz" -type f | wc -l | tr -d ' ')
        log "📊 Total backups: $BACKUP_COUNT"

        log "✅ Backup completed successfully!"
        exit 0
    else
        error "Failed to compress backup"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
else
    error "Failed to create database dump"
    rm -f "$BACKUP_FILE"
    exit 1
fi
