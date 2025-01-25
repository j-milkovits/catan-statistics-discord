FROM python:3.12-slim

WORKDIR /app

COPY requirements/deploy.txt .
RUN pip install --no-cache-dir -r deploy.txt

COPY . .
RUN pip install .


CMD ["python", "catan_statistics_discord/main.py"]
