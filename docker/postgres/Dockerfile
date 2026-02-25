FROM postgres:15

# Copy init script — runs automatically on first start (empty volume)
COPY init.sql /docker-entrypoint-initdb.d/

ENV POSTGRES_DB=mydb
ENV POSTGRES_USER=myuser
ENV POSTGRES_PASSWORD=mypassword
