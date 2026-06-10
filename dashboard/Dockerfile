FROM python:3.12-slim

WORKDIR /app
COPY dashboard/ .

CMD ["sh", "-c", "python3 -m http.server ${PORT:-8080}"]
