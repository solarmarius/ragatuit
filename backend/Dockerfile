# ---- Builder Stage ----
# This stage installs all our Python dependencies into a virtual environment.
FROM python:3.12-slim as builder

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Configure Poetry to create the virtual environment inside the project's folder
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Copy only the files needed to install dependencies
COPY pyproject.toml poetry.lock ./

# Install only production dependencies into the virtual environment
RUN poetry install --no-root


# ---- Final Stage ----
# This stage copies the pre-built virtual environment and our source code
# into a clean Python image to create a small, efficient production image.
FROM python:3.12-slim as final

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv ./.venv

# Activate the virtual environment by adding it to the system's PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy our application's source code
# We copy the inner `my_backend` folder from `src` to the root of our app
COPY src/backend/ ./backend/

# Command to run the application
# Uvicorn will be found in the venv's PATH
# The app is at `my_backend.main:app`
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "80"]