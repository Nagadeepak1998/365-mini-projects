FROM python:latest

RUN apt-get update && apt-get install -y curl
ADD ./src /app/src

CMD ["python", "app.py"]
