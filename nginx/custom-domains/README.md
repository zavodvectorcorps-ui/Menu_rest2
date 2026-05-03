# This directory holds per-tenant custom domain nginx configs
# (e.g. catch-menu.by.conf, menu-myatasportivnaya.by.conf).
#
# Populated by scripts/add-domain.sh. Git ignores the .conf files on purpose
# so that `update.sh` (which does `git reset --hard`) does NOT wipe them.
# Each VPS keeps its own list of tenant domains.
#
# The parent nginx.conf does `include /etc/nginx/custom-domains/*.conf;` at
# the end of the http {} block.
