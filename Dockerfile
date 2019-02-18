FROM python:3.6-jessie

ADD . /code
WORKDIR /code

RUN apt-get update -y && \
    apt-get install \
     build-essential \
     python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info -y && \
    python -m pip --no-cache install -r requirements.txt