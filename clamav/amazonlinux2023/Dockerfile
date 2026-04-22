FROM amazonlinux:2023

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN dnf install -y python3 wget shadow-utils \
    && wget -q https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.2/clamav-1.5.2.linux.x86_64.rpm -O /tmp/clamav.rpm \
    && echo "9c7e0532e718b3aec294ec08be7fdbd39969d922bb7bb93cc06d1da890c39848  /tmp/clamav.rpm" | sha256sum -c - \
    && dnf install -y --allowerasing /tmp/clamav.rpm \
    && rm -f /tmp/clamav.rpm \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && useradd -r -s /sbin/nologin clamav || true \
    && mkdir -p /var/lib/clamav \
    && chown clamav:clamav /var/lib/clamav \
    && echo "DatabaseMirror database.clamav.net" > /usr/local/etc/freshclam.conf \
    && echo "DatabaseDirectory /var/lib/clamav" >> /usr/local/etc/freshclam.conf \
    && freshclam \
    && dnf clean all
