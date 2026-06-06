# Tunnel Analysis Pipeline (headless, không có UI)
# Dùng cho: batch processing, OCR, RAG, export PDF/IFC
# Không bao gồm: PyQt/PySide6 GUI

FROM python:3.12-slim

WORKDIR /app

# System deps cho open3d, PaddleOCR, laspy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài (bỏ GUI packages)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    numpy==2.4.3 \
    scipy==1.17.1 \
    laspy==2.7.0 \
    lazrs==0.8.1 \
    scikit-learn==1.8.0 \
    pandas==3.0.3 \
    matplotlib==3.10.8 \
    openpyxl==3.1.5 \
    requests==2.32.5 \
    paddleocr==3.4.0 \
    paddlepaddle==3.2.1

# Copy source code
COPY tunnel_analysis/ ./tunnel_analysis/

ENV FLAGS_use_mkldnn=0
ENV FLAGS_use_onednn=0
ENV OLLAMA_HOST=http://ollama:11434

CMD ["python", "-m", "tunnel_analysis"]
