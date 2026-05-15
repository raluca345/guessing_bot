"""Database connection utilities."""
import configparser
import logging
import time
from contextlib import contextmanager

import mysql.connector

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config/config.ini')


def connect():
    """High-level method to establish a database connection."""
    config_db = {
        'user': config['mysqlDB']['user'],
        'password': config['mysqlDB']['pass'],
        'host': config['mysqlDB']['host'],
        'database': config['mysqlDB']['db']
    }
    return connect_to_db(config_db, attempts=3, delay=2)


def connect_to_db(config, attempts=3, delay=2):
    """Low-level method to connect to database with retries."""
    attempt = 1
    while attempt <= attempts:
        try:
            return mysql.connector.connect(**config, pool_name="pool", pool_size=10)
        except (mysql.connector.Error, IOError) as e:
            if attempt >= attempts:
                logger.error("Failed to connect, exiting without a connection: %s", e)
                return None

            logger.info(
                "Connection failed: %s. Retrying (%d/%d)...",
                e,
                attempt,
                attempts,
            )
            time.sleep(delay ** attempt)
            attempt += 1

    return None


@contextmanager
def temp_connect():
    """Context manager that yields a DB connection and ensures it is closed.

    Use this for short-lived DB work to guarantee connections are returned to
    the pool even on error.
    """
    conn = connect()
    try:
        yield conn
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
