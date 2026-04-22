FROM amazonlinux:2023

COPY aide/shared/aide-to-json.py /usr/local/bin/aide-to-json.py

RUN dnf install -y aide python3 \
    && chmod +x /usr/local/bin/aide-to-json.py \
    && aide --init -c /etc/aide.conf \
    && cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz \
    && dnf clean all
