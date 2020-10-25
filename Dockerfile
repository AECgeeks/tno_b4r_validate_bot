FROM debian:buster-slim
MAINTAINER Thomas Krijnen <thomas@aecgeeks.org>

RUN mkdir -p /usr/share/man/man1
RUN apt-get update -y && apt-get install -y curl openjdk-11-jdk-headless python3 python3-distutils git supervisor watch

RUN curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | python3
RUN python3 -m pip install rdflib flask tabulate gunicorn

WORKDIR /

ARG SHACLVERSION=1.3.2
ENV SHACLVERSION ${SHACLVERSION}
ENV SHACLROOT=/shacl-${SHACLVERSION}/bin
ENV PATH="${SHACLROOT}:${PATH}"

RUN curl --silent --show-error --retry 5 https://repo1.maven.org/maven2/org/topbraid/shacl/${SHACLVERSION}/shacl-${SHACLVERSION}-bin.zip -o - | jar x
RUN chmod +x /shacl-${SHACLVERSION}/bin/*

RUN git clone https://github.com/aothms/BIM4Ren_SHACLDB /shapes

ADD run_validate.py /

ADD wsgi.py main.py /
ADD templates/* /templates/

COPY supervisord.conf /etc/supervisord.conf

ENTRYPOINT supervisord -n
