FROM almalinux:9

# TARGETARCH is set by Docker buildx automatically (amd64 or arm64).
# Pick the matching Cisco Talos RPM. Only x86_64 and aarch64 are published.
ARG TARGETARCH
ARG CLAMAV_VERSION=1.5.2
ARG CLAMAV_SHA256_AMD64=9c7e0532e718b3aec294ec08be7fdbd39969d922bb7bb93cc06d1da890c39848
ARG CLAMAV_SHA256_ARM64=4e308f5df693b32c5ed5642e574efe18f8f61dcac2a3bfff8f33b4fafd3cf230

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN set -eux \
    && case "${TARGETARCH:-amd64}" in \
         amd64) RPM_ARCH=x86_64;  RPM_SHA=${CLAMAV_SHA256_AMD64} ;; \
         arm64) RPM_ARCH=aarch64; RPM_SHA=${CLAMAV_SHA256_ARM64} ;; \
         *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && RPM_URL="https://github.com/Cisco-Talos/clamav/releases/download/clamav-${CLAMAV_VERSION}/clamav-${CLAMAV_VERSION}.linux.${RPM_ARCH}.rpm" \
    && dnf install -y python3 wget shadow-utils \
    && wget -q "${RPM_URL}" -O /tmp/clamav.rpm \
    && echo "${RPM_SHA}  /tmp/clamav.rpm" | sha256sum -c - \
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
