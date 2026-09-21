FROM postgres:16

RUN apt-get update && apt-get install -y \
    postgresql-16-postgis-3 \
    postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

COPY ./docker/postgres/maintenance /usr/bin/maintenance
RUN chmod +x /usr/bin/maintenance/*
RUN mv /usr/bin/maintenance/* /usr/bin \
    && rmdir /usr/bin/maintenance