FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY /master/master_server.py .

CMD ["python", "master_server.py"]