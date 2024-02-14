FROM python:3.10.13-slim-bullseye
#FROM python:3.12.2-slim-bullseye 
#FROM python:3.11.8-bullseye
#FROM python:3.11.8-slim-bookworm
#FROM python:3.11.8-slim-bullseye

ADD src/requirements.txt /usr/src

WORKDIR /usr/src

RUN pip install -r requirements.txt

RUN mkdir -p /usr/data
ADD src .
RUN python gen_parquet.py

ENTRYPOINT ["python", "mem_leak.py"]
