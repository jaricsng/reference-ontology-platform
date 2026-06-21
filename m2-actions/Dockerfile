FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY shapes ./shapes

# Defaults assume the in-cluster service names; override via env.
ENV FUSEKI_ENDPOINT=http://fuseki:3030/hospital \
    OPA_URL=http://opa:8181/v1/data/hospital/authz/decision

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
