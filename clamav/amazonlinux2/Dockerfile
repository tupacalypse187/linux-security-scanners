FROM amazonlinux:2

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN yum install -y python3 wget shadow-utils \
    && wget -q https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.2/clamav-1.5.2.linux.x86_64.rpm -O /tmp/clamav.rpm \
    && yum install -y /tmp/clamav.rpm \
    && rm -f /tmp/clamav.rpm \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && useradd -r -s /sbin/nologin clamav || true \
    && mkdir -p /var/lib/clamav \
    && chown clamav:clamav /var/lib/clamav \
    && echo "DatabaseMirror database.clamav.net" > /usr/local/etc/freshclam.conf \
    && echo "DatabaseDirectory /var/lib/clamav" >> /usr/local/etc/freshclam.conf \
    && freshclam \
    && yum clean all
