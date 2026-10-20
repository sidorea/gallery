FROM nginx:alpine

# Alpine Container Hardening Standards (2026 Baseline)
RUN apk update && apk upgrade --no-cache && \
    apk add --no-cache bash ffmpeg findutils coreutils gawk tzdata \
                       python3 py3-pip py3-gunicorn py3-flask py3-dotenv docker-cli && \
    find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

# Prepare application, media, and staging directories
RUN mkdir -p /usr/share/nginx/html/files/thumbs/seek \
             /app/Media-Organizer-App/backups \
             /tmp/new_files

# Copy Media-Playlist-App configuration, player UI, and thumbnail generator
COPY Media-Playlist-App/nginx.conf /etc/nginx/conf.d/default.conf
COPY Media-Playlist-App/index.html /usr/share/nginx/html/index.html
COPY Media-Playlist-App/generate-thumbs.sh /usr/local/bin/generate-thumbs.sh
RUN chmod +x /usr/local/bin/generate-thumbs.sh

# Copy Media-Organizer-App into container
COPY Media-Organizer-App /app/Media-Organizer-App

# Copy and set up unified startup entrypoint
COPY Media-Playlist-App/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Zero attack surface: purge ffmpeg and apk caches from production runtime
RUN apk del ffmpeg 2>/dev/null || true && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# Strict least privilege & runtime directory permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 777 /usr/share/nginx/html/files && \
    chmod -R 777 /app/Media-Organizer-App/backups

EXPOSE 80 9083

STOPSIGNAL SIGTERM

ENTRYPOINT ["/entrypoint.sh"]
