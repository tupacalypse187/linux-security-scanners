FROM amazonlinux:2

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN amazon-linux-extras install -y epel \
    && yum install -y clamav clamav-update python3 \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && ln -s /usr/bin/freshclam /usr/local/bin/freshclam \
    && ln -s /usr/bin/clamscan /usr/local/bin/clamscan \
    && freshclam \
    && yum clean all
