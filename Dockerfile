FROM python:3.11.5-slim

WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3-dev \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY app.py ./app.py
COPY src/ ./src/
COPY data/ ./data/
COPY .streamlit/ ./.streamlit/

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
