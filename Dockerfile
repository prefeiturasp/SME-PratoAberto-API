FROM python:3.6-alpine3.8
ADD . /code
WORKDIR /code


RUN apk update && apk add --no-cache \
      --virtual=.build-dependencies \
      gcc \
      musl-dev \
      postgresql-dev \
      git \
      python3-dev \
      jpeg-dev \
      # Pillow
      zlib-dev \
      freetype-dev \
      lcms2-dev \
      openjpeg-dev \
      tiff-dev \
      tk-dev \
      tcl-dev \
      harfbuzz-dev \
      fribidi-dev && \
    python -m pip --no-cache install -U pip && \
    python -m pip --no-cache install -r requirements.txt && \
    apk del --purge .build-dependencies