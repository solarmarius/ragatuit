"""Create test database if it doesn't exist."""

import logging
import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add src directory to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_database() -> None:
    """Create the test database if it doesn't exist."""
    # Use the main database name to construct test database name
    test_db_name = f"{settings.POSTGRES_DB}_test"

    # Connect to PostgreSQL server (not to a specific database)
    connection_params = {
        "host": settings.POSTGRES_SERVER,
        "port": settings.POSTGRES_PORT,
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "database": "postgres",  # Connect to default postgres database
    }

    try:
        # Connect to PostgreSQL server
        logger.info(
            f"Connecting to PostgreSQL server at {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}"
        )
        conn = psycopg2.connect(**connection_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn.cursor() as cursor:
            # Check if test database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (test_db_name,)
            )

            if cursor.fetchone():
                logger.info(f"Test database '{test_db_name}' already exists")
            else:
                # Create test database
                logger.info(f"Creating test database '{test_db_name}'")
                cursor.execute(f'CREATE DATABASE "{test_db_name}"')
                logger.info(f"Successfully created test database '{test_db_name}'")

        conn.close()
        logger.info("Database setup completed successfully")

    except psycopg2.Error as e:
        logger.error(f"Error setting up test database: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def main() -> None:
    """Main function to create test database."""
    logger.info("Starting test database creation")
    create_test_database()
    logger.info("Test database creation completed")


if __name__ == "__main__":
    main()
