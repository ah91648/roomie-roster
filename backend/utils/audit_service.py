"""
Audit Service for RoomieRoster

This module provides functions to interact with the audit logging system,
allowing you to query audit history, track changes, and monitor data modifications.

Usage:
    from utils.audit_service import AuditService

    # Get recent audit logs
    logs = AuditService.get_recent_logs(limit=50)

    # Get history for a specific record
    history = AuditService.get_record_history('chores', chore_id)

    # Get user activity
    activity = AuditService.get_user_activity('user@example.com')
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import g, request
import logging

logger = logging.getLogger(__name__)


class AuditService:
    """Service for interacting with the audit logging system"""

    @staticmethod
    def get_db():
        """Get database connection from Flask app context"""
        from flask import current_app
        from utils.database_config import get_db_engine

        if not hasattr(g, 'db_engine'):
            g.db_engine = get_db_engine(current_app)

        return g.db_engine

    @staticmethod
    def is_audit_enabled() -> bool:
        """Check if audit logging is enabled (requires PostgreSQL)"""
        try:
            from flask import current_app
            from utils.database_config import DatabaseConfig

            db_config = DatabaseConfig(current_app)
            return db_config.is_database_enabled()
        except Exception:
            return False

    @staticmethod
    def get_recent_logs(
        limit: int = 100,
        offset: int = 0,
        table_name: Optional[str] = None,
        operation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit logs

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            table_name: Filter by table name (optional)
            operation: Filter by operation type: INSERT, UPDATE, DELETE (optional)

        Returns:
            List of audit log records
        """
        if not AuditService.is_audit_enabled():
            return []

        try:
            engine = AuditService.get_db()

            query = """
                SELECT
                    id,
                    table_name,
                    record_id,
                    operation,
                    changed_at,
                    changed_by,
                    old_values,
                    new_values,
                    changed_fields
                FROM audit_log
                WHERE 1=1
            """

            params = {}

            if table_name:
                query += " AND table_name = %(table_name)s"
                params['table_name'] = table_name

            if operation:
                query += " AND operation = %(operation)s"
                params['operation'] = operation.upper()

            query += " ORDER BY changed_at DESC LIMIT %(limit)s OFFSET %(offset)s"
            params['limit'] = limit
            params['offset'] = offset

            with engine.connect() as conn:
                result = conn.execute(query, params)
                logs = []

                for row in result:
                    logs.append({
                        'id': row[0],
                        'table_name': row[1],
                        'record_id': row[2],
                        'operation': row[3],
                        'changed_at': row[4].isoformat() if row[4] else None,
                        'changed_by': row[5],
                        'old_values': row[6],
                        'new_values': row[7],
                        'changed_fields': row[8]
                    })

                return logs

        except Exception as e:
            logger.error(f"Error getting recent audit logs: {str(e)}")
            return []

    @staticmethod
    def get_record_history(table_name: str, record_id: int) -> List[Dict[str, Any]]:
        """
        Get complete audit history for a specific record

        Args:
            table_name: Name of the table
            record_id: ID of the record

        Returns:
            List of audit log records for this specific record, ordered chronologically
        """
        if not AuditService.is_audit_enabled():
            return []

        try:
            engine = AuditService.get_db()

            query = """
                SELECT * FROM get_record_audit_history(%(table_name)s, %(record_id)s)
            """

            with engine.connect() as conn:
                result = conn.execute(query, {
                    'table_name': table_name,
                    'record_id': record_id
                })
                history = []

                for row in result:
                    history.append({
                        'id': row[0],
                        'operation': row[1],
                        'changed_at': row[2].isoformat() if row[2] else None,
                        'changed_by': row[3],
                        'old_values': row[4],
                        'new_values': row[5],
                        'changed_fields': row[6]
                    })

                return history

        except Exception as e:
            logger.error(f"Error getting record history: {str(e)}")
            return []

    @staticmethod
    def get_user_activity(
        user_email: str,
        limit: int = 100,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific user

        Args:
            user_email: Email of the user
            limit: Maximum number of records to return
            days: Only show activity from last N days (optional)

        Returns:
            List of audit log records for this user
        """
        if not AuditService.is_audit_enabled():
            return []

        try:
            engine = AuditService.get_db()

            query = """
                SELECT * FROM get_user_audit_logs(%(user_email)s, %(limit)s)
            """

            if days:
                query = """
                    SELECT
                        id,
                        table_name,
                        record_id,
                        operation,
                        changed_at,
                        old_values,
                        new_values
                    FROM audit_log
                    WHERE changed_by = %(user_email)s
                    AND changed_at >= %(cutoff_date)s
                    ORDER BY changed_at DESC
                    LIMIT %(limit)s
                """

                cutoff_date = datetime.now() - timedelta(days=days)

                with engine.connect() as conn:
                    result = conn.execute(query, {
                        'user_email': user_email,
                        'limit': limit,
                        'cutoff_date': cutoff_date
                    })
            else:
                with engine.connect() as conn:
                    result = conn.execute(query, {
                        'user_email': user_email,
                        'limit': limit
                    })

            activity = []
            for row in result:
                activity.append({
                    'id': row[0],
                    'table_name': row[1],
                    'record_id': row[2],
                    'operation': row[3],
                    'changed_at': row[4].isoformat() if row[4] else None,
                    'old_values': row[5],
                    'new_values': row[6]
                })

            return activity

        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}")
            return []

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """
        Get audit log statistics

        Returns:
            Dictionary containing audit statistics by table and user
        """
        if not AuditService.is_audit_enabled():
            return {
                'enabled': False,
                'by_table': [],
                'by_user': []
            }

        try:
            engine = AuditService.get_db()

            # Get stats by table
            query_table = "SELECT * FROM audit_stats_by_table"
            with engine.connect() as conn:
                result = conn.execute(query_table)
                by_table = []

                for row in result:
                    by_table.append({
                        'table_name': row[0],
                        'total_changes': row[1],
                        'unique_records': row[2],
                        'inserts': row[3],
                        'updates': row[4],
                        'deletes': row[5],
                        'first_change': row[6].isoformat() if row[6] else None,
                        'last_change': row[7].isoformat() if row[7] else None
                    })

            # Get stats by user
            query_user = "SELECT * FROM audit_stats_by_user"
            with engine.connect() as conn:
                result = conn.execute(query_user)
                by_user = []

                for row in result:
                    by_user.append({
                        'user_email': row[0],
                        'total_changes': row[1],
                        'tables_modified': row[2],
                        'inserts': row[3],
                        'updates': row[4],
                        'deletes': row[5],
                        'first_change': row[6].isoformat() if row[6] else None,
                        'last_change': row[7].isoformat() if row[7] else None
                    })

            return {
                'enabled': True,
                'by_table': by_table,
                'by_user': by_user
            }

        except Exception as e:
            logger.error(f"Error getting audit statistics: {str(e)}")
            return {
                'enabled': True,
                'error': str(e),
                'by_table': [],
                'by_user': []
            }

    @staticmethod
    def log_manual_entry(
        table_name: str,
        record_id: int,
        operation: str,
        notes: str,
        changed_by: Optional[str] = None
    ) -> bool:
        """
        Manually log an audit entry (for operations not tracked by triggers)

        Args:
            table_name: Name of the table
            record_id: ID of the record
            operation: Operation type (INSERT, UPDATE, DELETE)
            notes: Description of the change
            changed_by: Email of user making the change (optional, auto-detected)

        Returns:
            True if successful, False otherwise
        """
        if not AuditService.is_audit_enabled():
            return False

        try:
            engine = AuditService.get_db()

            # Auto-detect user if not provided
            if not changed_by:
                if hasattr(g, 'user') and g.user:
                    changed_by = g.user.get('email')

            # Get IP and user agent from request
            ip_address = request.remote_addr if request else None
            user_agent = request.headers.get('User-Agent') if request else None

            query = """
                INSERT INTO audit_log (
                    table_name,
                    record_id,
                    operation,
                    changed_by,
                    ip_address,
                    user_agent,
                    notes
                ) VALUES (
                    %(table_name)s,
                    %(record_id)s,
                    %(operation)s,
                    %(changed_by)s,
                    %(ip_address)s,
                    %(user_agent)s,
                    %(notes)s
                )
            """

            with engine.connect() as conn:
                conn.execute(query, {
                    'table_name': table_name,
                    'record_id': record_id,
                    'operation': operation.upper(),
                    'changed_by': changed_by,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'notes': notes
                })

            return True

        except Exception as e:
            logger.error(f"Error logging manual audit entry: {str(e)}")
            return False

    @staticmethod
    def archive_old_logs(retention_days: int = 90) -> int:
        """
        Archive old audit logs (delete entries older than specified days)

        Args:
            retention_days: Number of days to keep logs

        Returns:
            Number of records deleted
        """
        if not AuditService.is_audit_enabled():
            return 0

        try:
            engine = AuditService.get_db()

            query = "SELECT archive_old_audit_logs(%(retention_days)s)"

            with engine.connect() as conn:
                result = conn.execute(query, {'retention_days': retention_days})
                deleted_count = result.fetchone()[0]

            logger.info(f"Archived {deleted_count} old audit log entries")
            return deleted_count

        except Exception as e:
            logger.error(f"Error archiving old audit logs: {str(e)}")
            return 0
