FROM python:3.11-slim


WORKDIR /app


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY main.py .
COPY chat.py .
COPY test_main.py .

COPY docs/ ./docs/


EXPOSE 8000

# comando para arrancar Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
