# Self-contained Apache Jena Fuseki image (same version as local: 6.1.0).
# In-memory dataset /hospital with update enabled; data is loaded over HTTP
# after the pod starts (see m6-infra/load-data.sh).
FROM eclipse-temurin:21-jre

ARG FUSEKI_VERSION=6.1.0
WORKDIR /opt
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sSL -o fuseki.tar.gz \
       https://archive.apache.org/dist/jena/binaries/apache-jena-fuseki-${FUSEKI_VERSION}.tar.gz \
    && tar -xzf fuseki.tar.gz && rm fuseki.tar.gz \
    && mv apache-jena-fuseki-${FUSEKI_VERSION} fuseki \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/fuseki
ENV FUSEKI_BASE=/tmp/fuseki-base
EXPOSE 3030
CMD ["./fuseki-server", "--mem", "--update", "/hospital"]
