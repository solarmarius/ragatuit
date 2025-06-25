FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install fastapi uvicorn python-multipart

# Copy the mock server
COPY . .

# Expose port
EXPOSE 8001

# Run the server
CMD ["uvicorn", "oauth_mock_server:app", "--host", "0.0.0.0", "--port", "8001"]
