This document outlines the technical architecture for a standalone AI-powered quiz generation web application that integrates with the Canvas LMS. The chosen stack is centered around a **Python-first, open-source philosophy**, prioritizing flexibility, control over the AI pipeline, and alignment with the robust data science and machine learning ecosystem.

The architecture is designed to be modular, scalable, and observable. It consists of a decoupled frontend built with **React**, and a powerful, asynchronous Python backend. The backend is responsible for all business logic, handling the **Canvas OAuth 2.0 flow** to gain API access, and orchestrating the core AI-driven question generation process.

**Architectural Goals:**

- **Flexibility & Control:** Leverage open-source models and frameworks to avoid vendor lock-in and allow for deep customization of the AI pipeline.
- **Rapid Backend Development:** Utilize a modern Python framework (FastAPI) to build a performant and well-documented API.
- **Modern User Experience:** Employ a best-in-class JavaScript framework (React) to create a responsive and intuitive interface for teachers.
- **Observability:** Integrate a comprehensive, open-source monitoring stack to ensure reliability and simplify debugging for an on-premise deployment.

#### **2. High-Level System Architecture**

The system is composed of containerized services that communicate via REST APIs. The FastAPI backend acts as the central orchestrator, handling user authentication, serving the frontend, and managing all data and AI workflows.

```
+-------------------+      +-------------------------+      +--------------------+
|   Teacher's       |----->|  Our Application URL    |----->| University Server  |
|   Browser         |      | (e.g., quizgen.univ.edu)|      |  (On-Premise)      |
+-------------------+      +-------------------------+      +---------+----------+
         |                                                           |
         | 1. Interacts with React Frontend                          |
         |                                +--------------------------V------------+
         |                                |        FastAPI Backend (Python)       |
         |                                |        (Central Orchestrator)         |
         +------------------------------->|                                       |<------------------+
                                          +------------------+--------------------+                   | 2. Auth Flow
                                                             |                                        |
                                 +---------------------------+---------------------------+            |
                                 |          INTERNAL BACKEND SERVICES & CONNECTIONS      |            V
                                 |                                                       |      +-----------+
         +---------------+       |       +---------------+       +---------------+       |      | Canvas    |
         |  React Build  | <------------+  Serving Logic  +-----> |  RAG Pipeline |-----> |      | API &     |
         |  (Static)     |       |       +---------------+       | (LangGraph)   |       |      | OAuth2    |
         +---------------+       |                               +-------+-------+       |      +-----------+
                                 |                                       |               |
                                 |             /-------------------------+               |
                                 |            /                          |               |
                                 |   +-------V-------+          +-------V-------+       |
                                 |   |  PostgreSQL   |          |     Redis     |       |
                                 |   +---------------+          +---------------+       |
                                 |                                       |               |
                                 |             \-------------------------+               |
                                 |                                       |               |
                                 |   +-------V-------+          +-------V-------+       |
                                 |   |   Vector DB   |          |    LLM API    |       |
                                 |   +---------------+          +---------------+       |
                                 +-------------------------------------------------------+

```

**Workflow Overview:**

1. A teacher navigates directly to our application's website.
2. The teacher clicks a "Login with Canvas" button, initiating the standard Canvas OAuth 2.0 authorization flow, which is managed by the backend.
3. Upon successful authorization, Canvas redirects the teacher back to our application with an **authorization code**.
4. Our FastAPI backend securely exchanges this code for an **access token** and **refresh token**. These tokens are stored securely in the PostgreSQL database.
5. The teacher is now logged in. The React frontend is served, and all subsequent API calls to Canvas are made by our backend using the stored access token.
6. The **RAG (Retrieval-Augmented Generation) Pipeline** is initiated upon user request to generate a quiz, which is then stored and pushed back to Canvas via its API.

#### **3. Component Deep Dive**

##### **3.1. Frontend**

- **Technology:** **React with Vite**
- **Rationale:** React is the industry standard for building declarative user interfaces, backed by a massive ecosystem of libraries and developer tools. Paired with Vite, it provides an extremely fast development server and an optimized build process for a superior developer experience.
- **UI/Styling:** **Shadcn UI and Tailwind CSS**
- **Rationale:** This combination offers the best of both worlds. **Tailwind CSS** provides a utility-first framework for rapid, custom styling. **Shadcn UI** provides a collection of beautifully designed, accessible, and unstyled components that developers copy into their project and customize freely using Tailwind CSS, avoiding dependency bloat and ensuring full control over the final design.

- **Error Reporting & Telemetry:** A lightweight client-side monitoring tool (e.g., **Sentry** or an open-source alternative) will be integrated to capture JavaScript errors in teachers' browsers. This allows for correlating frontend issues with backend traces to quickly diagnose problems.
- **Key Responsibilities:**
  - Rendering the application's landing page and UI.
  - Initiating the OAuth 2.0 login flow.
  - Displaying generated MCQs for teacher review and editing.
  - Handling user interactions and making asynchronous API calls to the FastAPI backend.

##### **3.2. Backend**

- **Technology:** **Python 3.11+ with FastAPI**
- **Rationale:** FastAPI is an incredibly fast, modern Python web framework. Its use of Pydantic for data validation and automatic generation of OpenAPI documentation dramatically speeds up development and reduces errors. Its native async support is critical for efficiently handling I/O-bound operations like API calls to Canvas and LLM services.

- **Health Checks:** The application will expose `/health/live` and `/health/ready` endpoints. These are crucial for the monitoring system and enable more robust deployment strategies by verifying that a new build is fully operational before routing traffic to it.
- **Core Libraries:**
  - **Pydantic:** For data validation and settings management.
  - **SQLModel (or SQLAlchemy):** As the Object-Relational Mapper (ORM) for interacting with PostgreSQL.
  - **Alembic:** For handling database schema migrations.
  - **httpx:** A modern, async-capable HTTP client for handling the OAuth 2.0 token exchange and making all subsequent API calls to Canvas.
- **Key Responsibilities:**
  - Managing the Canvas **OAuth 2.0 authorization code flow**.
  - Securely storing and refreshing Canvas API access tokens.
  - Serving the optimized static frontend build in a production environment.
  - Providing API endpoints for the frontend (e.g., `GET /courses`, `POST /generate-quiz`).
  - Orchestrating the long-running question generation process using `BackgroundTasks`.

##### **3.3. LLM Integration & RAG Pipeline**

- **Orchestration Framework:** **LangChain & LangGraph**
- **Rationale:** **LangChain** provides a modular framework for building the initial RAG workflow. For more complex, stateful, and cyclical processes (e.g., allowing the AI to use tools, reflect on its output, and retry), **LangGraph** will be used. It allows for the construction of agent-like architectures as graphs, providing greater control and reliability for production-grade AI systems.
- **The RAG Process:**
  1. **Ingestion & Chunking:** Course content is fetched from Canvas. LangChain's `RecursiveCharacterTextSplitter` is used to break the content into small, semantically meaningful chunks.
  2. **Embedding:** Each chunk is converted into a vector embedding using an open-source model from **Hugging Face** (e.g., `all-MiniLM-L6-v2`).
  3. **Vector Storage:** The embeddings are stored and indexed in a dedicated **Vector Database**. **ChromaDB** is an excellent starting choice for its simplicity. For larger scale, **Weaviate** offers more powerful features.
  4. **Retrieval & Generation:** A query retrieves relevant text chunks from the vector database. These chunks are inserted into a prompt and sent to an LLM (e.g., a self-hosted **Mistral-7B** model or a commercial API like OpenAI's) to generate the questions.
- **Production Requirements for LangGraph:**
  - In production, the backend server serves the optimized static frontend build. LangGraph requires a Redis instance and a Postgres database. Redis is used as a pub-sub broker to enable streaming real time output from background runs. Postgres is used to store assistants, threads, runs, persist thread state and long term memory, and to manage the state of the background task queue with 'exactly once' semantics.
- **Configurable Retrieval:** Key RAG parameters (e.g., top-k chunks, similarity threshold) will be configurable via environment variables. This allows operators to tune the balance between quiz quality, speed, and computational cost without requiring a full redeployment.
- **Fail-Safe Fallback:** The system will be designed with a fail-safe mechanism. If the primary self-hosted LLM is offline, it can be configured to fall back to a hosted API (like OpenAI or Anthropic), ensuring service continuity. An alert will be triggered if this fallback is used.

##### **3.4. Database**

- **Technology:** **PostgreSQL & Redis**
- **Rationale:**
  - **PostgreSQL:** A powerful, reliable, and open-source relational database. It is the industry standard for applications requiring data integrity and will handle all primary application data.
  - **Redis:** A high-performance in-memory data store required by LangGraph for its pub/sub and task-streaming capabilities. It will also be used for caching and session management.
- **Proposed Data Model (PostgreSQL):**
  - `users`, `canvas_auth_tokens` (to store encrypted access/refresh tokens), `courses`, `quizzes`, `generated_questions`

##### **3.5. Logging & Monitoring**

A comprehensive, open-source observability stack will be deployed alongside the application to ensure system health, performance, and easier debugging.

- **Metrics (The "What"): Prometheus**
  - **Rationale:** The industry-standard tool for collecting time-series metrics. It will scrape data from the backend and the host server.
  - **Integration:** The FastAPI backend will expose a `/metrics` endpoint using a library like `fastapi-instrumentation`. A **Node Exporter** container will expose server metrics (CPU, RAM, Disk I/O).
- **Logs (The "Why"): Grafana Loki**
  - **Rationale:** A highly efficient log aggregation system designed for cloud-native environments. It simplifies log searching and correlation.
  - **Integration:** A **Promtail** agent, running as a container, will automatically discover and forward logs from all other Docker containers to the central Loki instance.
- **Traces (The "Where"): OpenTelemetry & Jaeger**
  - **Rationale:** Tracing provides a detailed view of a request's journey through the application stack. This is crucial for identifying performance bottlenecks.
  - **Integration:** The FastAPI backend will be instrumented with the **OpenTelemetry SDK** to generate trace data, which will be sent to a **Jaeger** instance for storage and visualization.
- **Visualization (Single Pane of Glass): Grafana**
  - **Rationale:** The premier open-source dashboarding tool. It will connect to Prometheus, Loki, and Jaeger, allowing operators to create unified dashboards that correlate metrics, logs, and traces in one place.
- **LLM Observability: Langfuse**
  - **Rationale:** A specialized tool for debugging and analyzing LLM applications. It provides detailed, step-by-step traces of LangChain/LangGraph executions, showing prompts, outputs, token counts, and latencies.
  - **Integration:** Langfuse will be run as a self-hosted service. A callback handler in the RAG pipeline code will send detailed execution data to the Langfuse instance.

**Key Practices:**

- **Alerting:** Key alerts will be configured in Grafana (e.g., "Canvas token refresh failure > 5 minutes," "RAG pipeline queue length > 100," "95th-percentile quiz gen latency > 30s").
- **Log Levels:** A clear logging policy will be enforced (e.g., `DEBUG` in dev, `INFO` in prod) with sampling for highly verbose components to manage storage costs.
- **Data Retention:** Policies for data retention will be established (e.g., metrics for 2 weeks, logs for 1 month, traces for 1 week) to manage finite on-premise storage.

#### 4. Production Readiness

##### **4.1. Deployment & DevOps**

- **Technology:** **Docker & Docker Compose** deployed to a **local university server**.
- **Rationale:** Containerizing all services ensures consistency. Docker Compose is ideal for orchestrating the entire application and monitoring stack on a single host server, meeting on-premise requirements.
- **Orchestration:** The `docker-compose.yml` file will define all services: the application itself (FastAPI, React), its databases (PostgreSQL, Redis, VectorDB), and the complete monitoring suite (Prometheus, Loki, Grafana, Jaeger, Langfuse, etc.).
- **CI/CD Pipeline:** A **GitHub Actions** workflow will automatically test and build Docker images, push them to a container registry, and then securely connect to the university server to pull the latest images and restart the services.

##### **4.2. Security & Secrets Management**

- **Secrets Management:** Canvas client secrets and LLM API keys will be injected into containers at runtime using **Docker Secrets** or a dedicated secrets manager like **HashiCorp Vault**, rather than being stored in environment variables.
- **OAuth Scopes:** The application will request the minimum required OAuth scopes from Canvas to adhere to the principle of least privilege.
- **Secure Redirects:** The Canvas OAuth configuration will have its redirect URI strictly locked down to the application's production domain to prevent open-redirect attacks.

##### **4.3. Reliability & Resilience**

- **Retry Policies:** The `httpx` client and RAG pipeline steps will be configured with retry logic and **exponential backoff** to handle transient failures from Canvas or LLM APIs.
- **Circuit Breaker:** A circuit-breaker pattern will be implemented for external calls. If a service like the Canvas API is down, the circuit will open, causing requests to fail fast and preventing system resources from being exhausted.
- **Dead-Letter Queue:** If a background quiz generation task fails repeatedly, it will be moved to a dead-letter queue in Redis for manual inspection by an operator, preventing it from blocking the main queue.

##### 4.4 Scalability and future considerations

- **Backend Scaling:** For an on-premise deployment, scaling can be achieved by allocating more resources (CPU/RAM) to the server or, for more advanced setups, by using a container orchestration tool like Docker Swarm or a lightweight Kubernetes distribution (K3s) across multiple university servers.
- **Database Scaling:** The on-premise PostgreSQL and Redis instances should be deployed with robust backup and recovery plans managed by the university's IT department.
- **Future Enhancements:**
  - **Fine-tuning Models:** The open-source nature of this stack allows for fine-tuning a language model on a dataset of high-quality educational content.
  - **Advanced RAG:** Implement more sophisticated retrieval strategies like re-ranking or query transformations.
  - **Analytics:** Add a dashboard to provide insights into application usage and the quality of generated quizzes.
