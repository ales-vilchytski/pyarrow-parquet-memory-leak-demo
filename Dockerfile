FROM python:3.10.13-slim-bullseye
#FROM python:3.12.2-slim-bullseye 
#FROM python:3.11.8-bullseye
#FROM python:3.11.8-slim-bookworm
#FROM python:3.11.8-slim-bullseye

ARG GENERATOR_ARGS=""

ADD src/requirements.txt /usr/src

WORKDIR /usr/src

RUN pip install -r requirements.txt

RUN mkdir -p /usr/data
ADD src .
RUN python gen_parquet.py ${GENERATOR_ARGS}

ENTRYPOINT ["python", "mem_leak.py"]
