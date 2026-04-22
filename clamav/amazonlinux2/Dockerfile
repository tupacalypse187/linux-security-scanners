FROM amazonlinux:2

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN amazon-linux-extras install -y epel \
    && yum install -y clamav clamav-update python3 \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && freshclam \
    && yum clean all
