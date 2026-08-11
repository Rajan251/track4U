#!/bin/bash
# =============================================================================
# Track4U Database Backup & Restore Script
# =============================================================================
# Usage:
#   ./scripts/backup-db.sh backup    — copy DB from container to ./data/
#   ./scripts/backup-db.sh restore   — copy latest backup back into container
#   ./scripts/backup-db.sh list      — list existing backups
# =============================================================================

set -e

CONTAINER="track4u_api"
BACKUP_DIR="./data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

case "${1:-backup}" in

  backup)
    echo "📦 Backing up Track4U database..."
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/app_${TIMESTAMP}.db"
    docker cp "${CONTAINER}:/app/data/app.db" "$BACKUP_FILE"
    # Also keep a latest.db symlink
    cp "$BACKUP_FILE" "$BACKUP_DIR/latest.db"
    echo "✅ Backup saved to: $BACKUP_FILE"
    echo "   latest.db updated."
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/app_*.db 2>/dev/null | tail -n +11 | xargs -r rm --
    echo "🧹 Old backups pruned (keeping last 10)."
    ;;

  restore)
    RESTORE_FILE="${2:-$BACKUP_DIR/latest.db}"
    if [ ! -f "$RESTORE_FILE" ]; then
      echo "❌ No backup file found at: $RESTORE_FILE"
      echo "   Usage: $0 restore [path/to/backup.db]"
      exit 1
    fi
    echo "⚠️  Restoring from: $RESTORE_FILE"
    echo "   This will OVERWRITE the current database. Are you sure? [y/N]"
    read -r confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
      echo "Aborted."
      exit 0
    fi
    docker cp "$RESTORE_FILE" "${CONTAINER}:/app/data/app.db"
    docker compose restart api
    echo "✅ Database restored and container restarted."
    ;;

  list)
    echo "📋 Available backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/*.db 2>/dev/null || echo "   (no backups found)"
    ;;

  *)
    echo "Usage: $0 {backup|restore [file]|list}"
    exit 1
    ;;

esac
