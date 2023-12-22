FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY /secondary/secondary_server.py .

CMD ["python", "secondary_server.py"]