FROM python:3.10-alpine3.16 as builder
WORKDIR /app

RUN apk update
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    python3-dev \
    musl-dev \
    postgresql-dev 
    
COPY LICENSE README.md requirements.txt setup.py .
COPY pitschi pitschi
COPY conf/pitschixapi.conf.example conf/

RUN pip install --no-cache-dir -r requirements.txt
RUN python setup.py install
