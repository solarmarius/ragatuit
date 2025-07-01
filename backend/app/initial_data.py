import logging

# Import all models to ensure SQLAlchemy can resolve relationships
import app.auth.models  # noqa
import app.question.models  # noqa
import app.quiz.models  # noqa
from app.database import get_session, init_db

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
