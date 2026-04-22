FROM amazonlinux:2023

COPY aide/shared/aide-to-json.py /usr/local/bin/aide-to-json.py
COPY aide/amazonlinux2023/native-json-demo.sh /usr/local/bin/native-json-demo.sh

RUN dnf install -y aide python3 \
    && chmod +x /usr/local/bin/aide-to-json.py /usr/local/bin/native-json-demo.sh \
    && aide --init -c /etc/aide.conf \
    && cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz \
    && dnf clean all
