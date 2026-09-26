FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi:app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN sed -i "s/\r$//" entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 2005

CMD ["sh", "./entrypoint.sh"]