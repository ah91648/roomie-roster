#!/bin/bash

# RoomieRoster Database Backup Script (AWS S3 Storage)
# This script creates a compressed backup of the PostgreSQL database
# and uploads it to AWS S3 for durable, off-site storage

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
TEMP_DIR="/tmp/roomieroster_backup"
BACKUP_FILE="$TEMP_DIR/roomieroster_backup_$TIMESTAMP.sql"
COMPRESSED_FILE="$BACKUP_FILE.gz"

# S3 Configuration
S3_BUCKET="${S3_BUCKET_NAME:-roomieroster-backups}"  # Override with env variable
S3_PATH="backups/roomieroster_backup_$TIMESTAMP.sql.gz"
RETENTION_DAYS=90  # Keep S3 backups for 90 days

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

# Cleanup function
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

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

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    error "AWS CLI not found. Please install it:"
    echo "  pip install awscli"
    echo "  aws configure"
    exit 1
fi

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    error "pg_dump not found. Please install PostgreSQL client tools:"
    echo "  macOS: brew install postgresql@15"
    echo "  Ubuntu: sudo apt-get install postgresql-client"
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    error "AWS credentials not configured. Run 'aws configure'"
    exit 1
fi

# Create temporary directory
mkdir -p "$TEMP_DIR"

log "Starting database backup to S3..."
log "S3 bucket: s3://$S3_BUCKET/$S3_PATH"

# Create the backup
if pg_dump "$DATABASE_URL" > "$BACKUP_FILE" 2>&1; then
    log "✅ Database dump created successfully"

    # Compress the backup
    if gzip "$BACKUP_FILE"; then
        log "✅ Backup compressed successfully"

        # Get file size
        SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        log "📦 Backup size: $SIZE"

        # Upload to S3
        log "☁️  Uploading to S3..."
        if aws s3 cp "$COMPRESSED_FILE" "s3://$S3_BUCKET/$S3_PATH" \
            --storage-class STANDARD_IA \
            --metadata "timestamp=$TIMESTAMP,app=roomieroster" \
            2>&1; then
            log "✅ Backup uploaded to S3 successfully"

            # Verify upload
            if aws s3 ls "s3://$S3_BUCKET/$S3_PATH" &> /dev/null; then
                log "✅ Upload verified"
            else
                error "Upload verification failed"
                exit 1
            fi

            # Clean up old backups in S3
            log "🧹 Cleaning up S3 backups older than $RETENTION_DAYS days..."

            # Calculate cutoff date
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                CUTOFF_DATE=$(date -v-${RETENTION_DAYS}d +%Y-%m-%d)
            else
                # Linux
                CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)
            fi

            # List and delete old backups
            aws s3 ls "s3://$S3_BUCKET/backups/" | while read -r line; do
                FILE_DATE=$(echo $line | awk '{print $1}')
                FILE_NAME=$(echo $line | awk '{print $4}')

                if [[ ! -z "$FILE_NAME" ]] && [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
                    log "  Deleting old backup: $FILE_NAME"
                    aws s3 rm "s3://$S3_BUCKET/backups/$FILE_NAME"
                fi
            done

            # Get backup count
            BACKUP_COUNT=$(aws s3 ls "s3://$S3_BUCKET/backups/" | grep ".sql.gz" | wc -l | tr -d ' ')
            log "📊 Total S3 backups: $BACKUP_COUNT"

            log "✅ Backup to S3 completed successfully!"
            exit 0
        else
            error "Failed to upload to S3"
            exit 1
        fi
    else
        error "Failed to compress backup"
        exit 1
    fi
else
    error "Failed to create database dump"
    exit 1
fi
