FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    wget \
    git \
    vim \
    nano \
    sudo \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    net-tools \
    iputils-ping \
    telnet \
    netcat \
    openssh-client \
    ca-certificates \
    gnupg \
    lsb-release

WORKDIR /app

COPY . /app

RUN pip3 install -r requirements.txt

CMD ["python3", "app.py"]