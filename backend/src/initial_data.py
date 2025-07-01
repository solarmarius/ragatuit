import logging

# Import all models to ensure SQLAlchemy can resolve relationships
import src.auth.models  # noqa
import src.question.models  # noqa
import src.quiz.models  # noqa
from src.database import get_session, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    with get_session() as session:
        init_db(session)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
