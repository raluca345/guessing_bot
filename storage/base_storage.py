from contextlib import closing

from utility.db import temp_connection
from utility.utility_functions import logger


class BaseStorage:
    """Base class for database storage classes with common query logic."""

    def __init__(self, use_dictionary: bool = True) -> None:
        self.use_dictionary = use_dictionary

    def _load(self, query: str, params=None):
        """Fetch rows using a short-lived database connection."""
        with temp_connection() as connection:
            with closing(connection.cursor(dictionary=self.use_dictionary)) as cursor:
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()

    def execute_insert(self, query: str, params=None):
        """Execute an INSERT/UPDATE/DELETE query and commit."""
        try:
            with temp_connection() as connection:
                with closing(connection.cursor(dictionary=self.use_dictionary)) as cursor:
                    if params is not None:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    connection.commit()
        except Exception:
            logger.exception("Failed to execute insert query")
