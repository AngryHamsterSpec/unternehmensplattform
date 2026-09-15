FROM postgres:18.6-alpine@sha256:d3e1620b530c944afa6e887d22eb899824da68e19c52024bf98f5220c88a65b2
# Den einen UID-Wechsel auf Alpines gepflegtes su-exec umstellen.
# Das alte Go-Programm vollständig entfernen, damit auch die Imageanalyse
# keinen überholten Binärbefund aus einer Basisschicht übernimmt.
RUN apk add --no-cache libuuid=2.42.3-r1 libcrypto3=3.5.8-r0 libssl3=3.5.8-r0 su-exec=0.3-r0 \
    && test "$(grep -c 'exec gosu postgres' /usr/local/bin/docker-entrypoint.sh)" = 1 \
    && sed -i 's/exec gosu postgres/exec su-exec postgres/' /usr/local/bin/docker-entrypoint.sh \
    && ! grep -q gosu /usr/local/bin/docker-entrypoint.sh \
    && rm /usr/local/bin/gosu \
    && test "$(su-exec postgres id -u)" = "$(id -u postgres)"
