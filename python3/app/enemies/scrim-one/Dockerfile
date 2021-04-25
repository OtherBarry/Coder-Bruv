FROM python:3-alpine

COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN python -m pip install -r requirements.txt
COPY . /app/
COPY app/enemies/scrim-one/agent.py agent.py
ENTRYPOINT PYTHONUNBUFFERED=1 python agent.py
