FROM python:3.5-alpine3.8
ADD . /code
WORKDIR /code
RUN python -m pip --no-cache install -r requirements.txt
