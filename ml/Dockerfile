FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir transformers==4.56.2 peft==0.17.1 trl==0.23.0 bitsandbytes==0.47.0 \
    accelerate==1.10.1 datasets==4.1.1 fastapi==0.118.0 uvicorn==0.37.0 anthropic sentencepiece protobuf edge-tts pytest httpx
WORKDIR /ml
ENV HF_HOME=/ml/hf
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
