FROM almalinux:9

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN dnf install -y epel-release \
    && dnf install -y clamav clamav-update python3 \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && freshclam \
    && dnf clean all
