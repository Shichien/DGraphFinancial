FROM flink:1.19.1-scala_2.12-java17

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl ca-certificates \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && pip3 install --no-cache-dir apache-flink==1.19.1 requests \
    && curl -fSL https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.2.0-1.19/flink-sql-connector-kafka-3.2.0-1.19.jar \
      -o /opt/flink/lib/flink-sql-connector-kafka-3.2.0-1.19.jar \
    && rm -rf /var/lib/apt/lists/*

USER flink
