FROM python:3.11-slim
RUN pip install boto3
COPY ecs_task_runner.py /app/ecs_task_runner.py
WORKDIR /app
ENTRYPOINT ["python", "ecs_task_runner.py"]