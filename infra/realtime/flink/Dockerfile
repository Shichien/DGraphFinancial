FROM flink:1.19.1-scala_2.12-java17

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir apache-flink==1.19.1

ENV PYFLINK_CLIENT_EXECUTABLE=/usr/bin/python3
ENV PYFLINK_PYTHON=/usr/bin/python3

RUN mkdir -p /opt/flink/lib /opt/dgcheater/jobs \
    && curl -fsSL -o /opt/flink/lib/flink-sql-connector-kafka-3.2.0-1.19.jar \
       https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.2.0-1.19/flink-sql-connector-kafka-3.2.0-1.19.jar
