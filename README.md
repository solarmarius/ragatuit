# Rag@UiT – Generating multiple-choice questions with a language model

Rag@UiT is an application that helps instructors and course coordinators generate multiple-choice questions (MCQs) based on the content of their courses from the Canvas LMS. The goal is to streamline the creation of a question bank that can be used to build quizzes and exams.

## Key Features

- **Canvas Integration:**
  - Secure login using Canvas credentials (OAuth2).
  - Browse your Canvas courses and select content (modules, pages, files) for question generation.
- **AI-Powered Question Generation:**
  - Utilizes a Language Model (LLM) to analyze course materials (text, PDFs).
  - Generates relevant multiple-choice questions based on the selected content.
- **Question Review & Management:**
  - Review generated MCQs, including questions and answer choices.
  - Approve, skip, or edit questions to ensure quality and accuracy.
- **Export to Canvas:**
  - Compile approved questions into a quiz.
  - Export the quiz directly back to your Canvas course.
  - Option to export questions in JSON format.
- **User-Friendly Interface:**
  - Modern, responsive web interface.
  - Progress tracking for question generation tasks.

_(Planned Enhancements: Saving drafts, support for multiple LLM models, expanded question types beyond MCQ.)_

## Tech Stack

**Backend:**

- **Framework:** FastAPI (Python)
- **ORM:** SQLModel (Pydantic + SQLAlchemy)
- **Database:** PostgreSQL
- **Async Support:** `httpx` for Canvas API calls
- **Authentication:** JWT, Passlib, python-jose (for Canvas OAuth2 callback handling)
- **Migrations:** Alembic
- **Content Parsing:** Beautiful Soup (bs4), PyPDF

**Frontend:**

- **Framework:** React (with TypeScript)
- **Build Tool:** Vite
- **UI Library:** Chakra UI
- **Routing:** TanStack Router
- **Data Fetching/State:** TanStack Query
- **API Client:** Auto-generated from OpenAPI spec using `@hey-api/openapi-ts`

**Infrastructure & DevOps:**

- **Containerization:** Docker, Docker Compose
- **Reverse Proxy & Load Balancer:** Traefik (handles routing, SSL)
- **Database Admin:** Adminer
- **Logging & Monitoring:** Grafana, Loki, Promtail
- **Testing:**
  - Backend: Pytest, Coverage
  - Frontend: Playwright (E2E)
- **CI/CD:** GitHub Actions
- **Linting/Formatting:** Ruff, Mypy, Bandit (Backend); Biome (Frontend); pre-commit hooks

## Architecture Overview

Rag@UiT is a full-stack web application with a monorepo structure:

- **Backend (`/backend`):** A FastAPI application serving a RESTful API. It handles business logic, Canvas API interactions, LLM communication, user authentication, and database operations (PostgreSQL via SQLModel).
- **Frontend (`/frontend`):** A React (TypeScript) single-page application (SPA) providing the user interface. It communicates with the backend API to display information and trigger actions.
- **Database:** PostgreSQL stores user data, course information, generated questions, etc. Alembic manages schema migrations.
- **Services:** Docker Compose manages all services, including the application containers, database, Traefik, Adminer, and the logging stack (Loki, Promtail, Grafana).
- **`/docs`:** Contains detailed documentation on development, deployment, roadmap, etc.
- **`/scripts`:** Utility scripts for tasks like building, testing, and generating the API client.

## Getting Started (Local Development)

The quickest way to get the full application stack running locally is with Docker Compose.

**Prerequisites:**

- Git
- Docker and Docker Compose

**Steps:**

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create and configure the environment file:**

    - The application uses a `.env` file in the project root for configuration. You'll need to create this file.
    - Populate `.env` with the necessary variables. Key variables include:

      ```env
      # .env (Example - Replace with your actual values)
      PROJECT_NAME="Rag@UiT"

      # PostgreSQL Settings
      POSTGRES_SERVER=db
      POSTGRES_USER=myuser         # Choose a username
      POSTGRES_PASSWORD=mypassword # Choose a strong password
      POSTGRES_DB=rag_uit_dev      # Choose a database name

      # Backend Settings
      SECRET_KEY=your_very_strong_and_unique_secret_key # Generate with: openssl rand -hex 32
      FRONTEND_HOST=http://localhost:5173
      ENVIRONMENT=local # local, staging, or production

      # Canvas API Credentials (Register your app in Canvas Developer Keys)
      CANVAS_CLIENT_ID=your_canvas_client_id
      CANVAS_CLIENT_SECRET=your_canvas_client_secret
      CANVAS_REDIRECT_URI=http://localhost:8000/api/v1/auth/canvas/callback # Adjust if your backend runs elsewhere
      CANVAS_BASE_URL=https://your-canvas-instance.instructure.com # e.g., https://canvas.uit.no

      # Default Admin User (created by prestart script)
      FIRST_SUPERUSER=admin@example.com
      FIRST_SUPERUSER_PASSWORD=your_admin_password # Choose a strong password

      # Domain for Traefik (optional for basic local dev, needed for domain-based routing)
      # If you want to test with subdomains like api.localhost.tiangolo.com:
      # DOMAIN=localhost.tiangolo.com
      # STACK_NAME=raguit # Used for Traefik labels, can be any string

      # SMTP Settings (Optional, for email features like password recovery)
      # SMTP_HOST=
      # SMTP_PORT=
      # SMTP_USER=
      # SMTP_PASSWORD=
      # EMAILS_FROM_EMAIL=
      ```

    - **Important:** Replace placeholder values with your actual configuration, especially `SECRET_KEY`, database credentials, and Canvas API details.
    - Refer to `backend/app/core/config.py` for a comprehensive list of backend settings.

3.  **Start the application stack:**

    ```bash
    docker compose watch
    ```

    This command builds the Docker images (if not already built) and starts all services. The `watch` command enables live reloading for some services during development.

4.  **Access the application:**

    - **Frontend:** [http://localhost:5173](http://localhost:5173)
    - **Backend API:** [http://localhost:8000](http://localhost:8000)
    - **API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
    - **Adminer (Database Admin):** [http://localhost:8080](http://localhost:8080)
    - **Traefik Dashboard:** [http://localhost:8090](http://localhost:8090) (If Traefik is part of the default compose setup, or if `DOMAIN` is set)

    _Note: The first time you start, it might take a few minutes for the database to initialize and migrations to run._

## Development

For more detailed information on:

- Setting up individual backend or frontend development environments (without Docker for those specific parts).
- Running linters, formatters, and pre-commit hooks.
- Generating the API client.

Please refer to the [Development Documentation (`docs/development.md`)](docs/development.md).

- Backend specific details: [`backend/README.md`](backend/README.md)
- Frontend specific details: [`frontend/README.md`](frontend/README.md)

## Testing

- **Backend tests (Pytest):**
  ```bash
  # From the project root
  docker compose exec backend bash scripts/tests-start.sh
  # Or, to run tests with the local Python environment (see backend/README.md):
  # cd backend
  # pytest
  ```
- **Frontend End-to-End tests (Playwright):**
  Ensure the Docker stack is running (`docker compose up -d --wait backend`).
  ```bash
  # From the project root
  cd frontend
  npx playwright test
  ```
  Refer to `frontend/README.md` for more on Playwright testing.

## License

This project is licensed under the [MIT License]
