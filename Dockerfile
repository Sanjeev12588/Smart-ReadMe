# Stage 1: Build the Vite frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Run the FastAPI backend
FROM python:3.12-slim
WORKDIR /app

# Install git (required for cloning public repo URLs in the API)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install them
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code files
COPY api.py config.py app.py cli.py ./
COPY agents/ ./agents/
COPY mcp/ ./mcp/
COPY tools/ ./tools/
COPY prompts/ ./prompts/

# Copy built frontend static assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose default port
EXPOSE 8050

# Default environment variables
ENV HOST=0.0.0.0
ENV PORT=8050
ENV RELOAD=false

# Start server using python entrypoint
CMD ["python", "api.py"]
