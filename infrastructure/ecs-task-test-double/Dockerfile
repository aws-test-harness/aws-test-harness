FROM python:3.11-slim AS builder
WORKDIR /tmp
RUN pip install uv
COPY pyproject.toml .
RUN uv export --format requirements.txt > requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /tmp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt
COPY src/ecs_task_runner.py .
ENTRYPOINT ["python", "ecs_task_runner.py"]