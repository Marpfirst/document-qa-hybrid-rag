# Backend image, sized for a free Hugging Face Space (2 vCPU / 16 GB).
FROM python:3.11-slim

# HF Spaces runs the container as uid 1000.
RUN useradd -m -u 1000 app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/app/.cache/huggingface \
    FASTEMBED_CACHE_PATH=/home/app/.cache/fastembed \
    QDRANT_PATH=/home/app/data/qdrant

WORKDIR /home/app

COPY --chown=app:app api/pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r pyproject.toml

COPY --chown=app:app api/app ./app

USER app

# Bake the models into the image. Downloading them at boot instead would make
# every cold start pay ~200 MB of transfer, on top of the container spin-up
# that already keeps the first visitor waiting.
RUN python -c "\
from fastembed import TextEmbedding, SparseTextEmbedding; \
from sentence_transformers import CrossEncoder; \
TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
SparseTextEmbedding(model_name='Qdrant/bm25'); \
CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'); \
print('models cached')"

RUN mkdir -p /home/app/data/qdrant

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
