FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py security.py server.py ./

# In-cluster defaults. OLLAMA runs on the HOST, reached via host.k3d.internal.
ENV FUSEKI_ENDPOINT=http://fuseki:3030/hospital \
    OPA_URL=http://opa:8181/v1/data/hospital/authz/decision \
    OLLAMA_BASE_URL=http://host.k3d.internal:11434 \
    OLLAMA_MODEL=qwen2.5-coder:7b

EXPOSE 8002
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8002"]
