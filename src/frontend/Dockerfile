FROM python:3.11-slim

WORKDIR /app

COPY requirements-frontend.txt .
RUN pip install --no-cache-dir -r requirements-frontend.txt

COPY src/frontend ./src/frontend

EXPOSE 8501

CMD ["streamlit", "run", "src/frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501"]