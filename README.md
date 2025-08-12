# Rag@UiT - AI-Powered Quiz Generator for Canvas

Rag@UiT is a powerful web application designed to help instructors and course coordinators streamline the creation of high-quality quizzes for their courses in the Canvas LMS. By leveraging the power of Large Language Models (LLMs), Rag@UiT analyzes your course materials and automatically generates relevant questions, significantly reducing the time and effort required to create a robust question bank.

## Key Features

-   **Seamless Canvas Integration**:
    -   Securely log in using your existing Canvas credentials via OAuth2.
    -   Browse your Canvas courses and select content (modules, pages, files) to be used for question generation.
-   **AI-Powered Question Generation**:
    -   Utilizes LLMs to analyze course materials, including text and PDF files.
    -   Generates a variety of question types (initially Multiple-Choice Questions).
    -   Supports question generation in multiple languages (English and Norwegian).
-   **Comprehensive Review Workflow**:
    -   Review, edit, approve, or reject generated questions to ensure quality and accuracy.
    -   A clear and intuitive interface for managing the question bank.
-   **Direct-to-Canvas Export**:
    -   Compile approved questions into a quiz.
    -   Export the quiz directly back to your Canvas course with a single click.
-   **Real-time Progress Tracking**:
    -   A consolidated status system tracks the entire quiz creation lifecycle, from content extraction to final publication.
    -   Visual indicators provide immediate feedback on the status of your quiz generation tasks.

## Architecture Overview

Rag@UiT is a full-stack web application built with a modern, containerized architecture.

-   **Backend**: A robust API built with **FastAPI** (Python) that handles all business logic, including Canvas API communication, LLM interactions, user authentication, and database operations.
-   **Frontend**: A responsive and user-friendly single-page application (SPA) built with **React** and **TypeScript**. It provides a rich user interface for interacting with the backend services.
-   **Database**: A **PostgreSQL** database stores all application data, including users, courses, quizzes, and questions. **Alembic** is used for database migrations.
-   **Infrastructure**: The entire application stack is containerized using **Docker** and managed with **Docker Compose**. This includes the application services, database, a **Traefik** reverse proxy, and a **Grafana/Loki** stack for monitoring and logging.

### Status System

A core feature of the application is its robust status system, which tracks a quiz through its entire lifecycle. This provides clear feedback to the user and allows for detailed error tracking.

-   **States**: `created` -> `extracting_content` -> `generating_questions` -> `ready_for_review` -> `exporting_to_canvas` -> `published`
-   **Failure Tracking**: A `failed` state, coupled with a specific reason, allows for easy debugging of issues in the generation process.

## Tech Stack

| Category             | Technology                                                                                                  |
| -------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Backend**          | [Python](https://www.python.org/), [FastAPI](https://fastapi.tiangolo.com/), [SQLModel](https://sqlmodel.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/) |
| **Frontend**         | [TypeScript](https://www.typescriptlang.org/), [React](https://reactjs.org/), [Vite](https://vitejs.dev/), [TanStack Router & Query](https://tanstack.com/), [Chakra UI](https://chakra-ui.com/) |
| **Database**         | [PostgreSQL](https://www.postgresql.org/)                                                                   |
| **Infrastructure**   | [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/), [Traefik](https://traefik.io/traefik/) |
| **Testing**          | [Pytest](https://pytest.org/) (Backend), [Playwright](https://playwright.dev/) (Frontend E2E)                 |
| **DevOps & Linting** | [GitHub Actions](https://github.com/features/actions), [uv](https://github.com/astral-sh/uv), [Ruff](https://beta.ruff.rs/), [MyPy](https://mypy-lang.org/), [Biome](https://biomejs.dev/), [pre-commit](https://pre-commit.com/) |
| **Monitoring**       | [Grafana](https://grafana.com/), [Loki](https://grafana.com/oss/loki/), [Promtail](https://grafana.com/docs/loki/latest/clients/promtail/) |

## Project Structure

The project is organized as a monorepo to facilitate development and deployment.

```
/
├── backend/          # FastAPI backend application
├── frontend/         # React frontend application
├── docs/             # In-depth project documentation
├── scripts/          # Utility and helper scripts
├── .github/          # GitHub Actions CI/CD workflows
├── docker-compose.yml# Main Docker Compose configuration
└── README.md         # This file
```

## Getting Started (Local Development)

The fastest way to get the entire application stack running locally is with Docker.

**Prerequisites:**
*   Git
*   Docker & Docker Compose

**1. Clone the repository:**

```bash
git clone <repository-url>
cd <repository-name>
```

**2. Configure your environment:**

Create a `.env` file in the project root by copying the example.
A `.env.example` file is provided at the root of this project. Copy this file to `.env` and fill in the required values.

```bash
cp .env.example .env
```

You will need to fill in the following critical variables:
*   `SECRET_KEY`: A strong, unique secret key. You can generate one with `openssl rand -hex 32`.
*   `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Credentials for your local database.
*   `CANVAS_CLIENT_ID`, `CANVAS_CLIENT_SECRET`: Your Canvas Developer Key credentials.
*   `CANVAS_BASE_URL`: The base URL of your Canvas instance (e.g., `https://canvas.uit.no`).

**3. Start the application:**

```bash
docker compose watch
```

This command builds the Docker images and starts all services with hot-reloading enabled for the frontend and backend.

**4. Access the services:**

Once the stack is running, you can access the different parts of the application:

-   **Frontend**: [http://localhost:5173](http://localhost:5173)
-   **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
-   **Traefik Dashboard**: [http://localhost:8090](http://localhost:8090)
-   **Grafana Dashboard**: [http://localhost:3000](http://localhost:3000)

## Development Workflow

While the entire stack runs in Docker, development is typically focused on either the backend or the frontend. For detailed instructions on setting up a local development environment, running linters, and other service-specific tasks, please refer to the README files in their respective directories:

-   **Backend Development**: [`backend/README.md`](backend/README.md)
-   **Frontend Development**: [`frontend/README.md`](frontend/README.md)

### Generating the Frontend API Client

The frontend uses a generated TypeScript client to communicate with the backend API. After making changes to the backend API, you should regenerate this client by running the script from the project root:

```bash
./scripts/generate-client.sh
```

## Testing

The project includes a comprehensive test suite for both the backend and frontend.

-   **Backend (Pytest)**:
    ```bash
    # Run tests against the running services
    docker compose exec backend bash scripts/tests-start.sh
    ```
-   **Frontend (Playwright E2E)**:
    ```bash
    # Ensure the stack is running, then run from the frontend directory
    cd frontend
    npx playwright test
    ```

For more detailed testing instructions, see the service-specific READMEs.

## CI/CD

This project uses **GitHub Actions** for Continuous Integration and Continuous Deployment. Workflows are defined in the `.github/workflows` directory and include jobs for:
-   Linting and formatting checks
-   Running backend and frontend tests
-   Building and pushing Docker images

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
