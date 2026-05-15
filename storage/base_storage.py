from utility.utility_functions import logger
from utility.db import connect


class BaseStorage:
    """Base class for database storage classes with common connection and query logic."""

    def __init__(self, use_dictionary: bool = True) -> None:
        self.connection = connect()
        self.cursor = self.connection.cursor(dictionary=use_dictionary)
        self.use_dictionary = use_dictionary

    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed."""
        try:
            self.connection.ping(reconnect=True, attempts=3, delay=2)
        except Exception:
            logger.warning("Database connection lost, reconnecting...")
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = connect()
        try:
            self.cursor.close()
        except Exception:
            pass
        self.cursor = self.connection.cursor(dictionary=self.use_dictionary)

    def close(self):
        """Close database cursor and connection."""
        if self.cursor is not None:
            try:
                self.cursor.close()
            except Exception:
                pass
            self.cursor = None
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    def execute_query(self, query: str, params=None):
        """Execute a SELECT query and return results."""
        self._ensure_connection()
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()

    def execute_insert(self, query: str, params=None):
        """Execute an INSERT/UPDATE/DELETE query and commit."""
        try:
            self._ensure_connection()
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
        except Exception:
            logger.exception("Failed to execute insert query")
