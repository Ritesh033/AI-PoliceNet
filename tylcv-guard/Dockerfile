FROM python:3.12-slim
WORKDIR /srv
COPY . .
ENV TYLCV_DB=/srv/data/tylcv.db
EXPOSE 8080
CMD ["python", "-m", "app.server", "--host", "0.0.0.0", "--port", "8080"]
