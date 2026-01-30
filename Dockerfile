# The builder image, used to build the virtual environment
FROM python:3.11.7-slim AS runtime

WORKDIR /app

COPY requirements.txt ./
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/* && PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY fonts ./fonts
COPY main.py ./main.py

ENTRYPOINT ["python3", "main.py"]