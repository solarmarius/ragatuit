# Rag@UiT – Generating multiple-choice questions with a language model

Rag@UiT is an app that generates multiple-choice questions based on the content of a course from Canvas.
The goal is to help instructors and course coordinators build a question bank that can later be used to automatically assemble exams.

## Functionalities

- Authentication with Canvas: The user logs in to gain access to their courses.
- Choice of course and modules: The user selects which Canvas course to generate questions from.
- Generation of questions: A language model is used to analyze the course content and generate multiple-choice questions.
- Question review: The user can approve or skip generated questions.
- Generation of exam: Once the questions are approved, an exam is generated directly in Canvas.
- Summary and progress: The user receives feedback on how many questions have been generated and how many remain.

> See Brukerflow.pdf in the project for an intended user flow for the application.

## Technology Stack and Features

- ⚡ [**FastAPI**](https://fastapi.tiangolo.com) for the Python backend API.
  - 🧰 [SQLModel](https://sqlmodel.tiangolo.com) for the Python SQL database interactions (ORM).
  - 🔍 [Pydantic](https://docs.pydantic.dev), used by FastAPI, for the data validation and settings management.
  - 💾 [PostgreSQL](https://www.postgresql.org) as the SQL database.
- 🚀 [React](https://react.dev) for the frontend.
  - 💃 Using TypeScript, hooks, Vite, and other parts of a modern frontend stack.
  - 🎨 [Chakra UI](https://chakra-ui.com) for the frontend components.
  - 🤖 An automatically generated frontend client.
  - 🧪 [Playwright](https://playwright.dev) for End-to-End testing.
  - 🦇 Dark mode support.
- 🐋 [Docker Compose](https://www.docker.com) for development and production.
- 🔒 Secure password hashing by default.
- 🔑 JWT (JSON Web Token) authentication.
- 📫 Email based password recovery.
- ✅ Tests with [Pytest](https://pytest.org).
- 📞 [Traefik](https://traefik.io) as a reverse proxy / load balancer.
- 🚢 Deployment instructions using Docker Compose, including how to set up a frontend Traefik proxy to handle automatic HTTPS certificates.
- 🏭 CI (continuous integration) and CD (continuous deployment) based on GitHub Actions.
