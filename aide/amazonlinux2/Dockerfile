FROM amazonlinux:2

COPY aide/shared/aide-to-json.py /usr/local/bin/aide-to-json.py

RUN yum install -y aide python3 \
    && chmod +x /usr/local/bin/aide-to-json.py \
    && aide --init \
    && cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz \
    && yum clean all
