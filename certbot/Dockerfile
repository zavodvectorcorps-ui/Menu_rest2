FROM certbot/certbot

# docker-cli is needed so certbot can send `nginx -s reload` to the nginx
# container via the host docker socket after a successful renewal.
# Without this, Nginx keeps serving the OLD (cached at startup) certificate
# even after certbot has written a renewed cert to disk — which manifests
# as a sudden "сертификат истёк" 60-90 days after deploy.
RUN apk add --no-cache docker-cli
