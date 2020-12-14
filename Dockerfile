FROM python:3.8-slim
WORKDIR /bot
COPY bot.py ./
COPY en_words.csv ./
COPY es_words.csv ./
COPY requirements.txt .
RUN pip install -qr requirements.txt