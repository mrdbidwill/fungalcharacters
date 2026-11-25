#!/bin/bash
# One-time server setup, run as root on the VPS (Claude runs it over SSH once Will has added the key in hPanel).
# Creates the deploy user "fc" with the same limited pattern as gulfcoastfungi's "gcf" user. Only adds things;
# nothing belonging to other sites is changed.
set -euo pipefail
id fc >/dev/null 2>&1 || useradd --create-home --shell /bin/bash fc
usermod -aG docker fc
install -d -m 700 -o fc -g fc /home/fc/.ssh
# The key Will added through hPanel lands in root's authorized_keys; copy it for fc (removed from root afterwards).
grep -h "fungalcharacters-deploy" /root/.ssh/authorized_keys > /home/fc/.ssh/authorized_keys
chown fc:fc /home/fc/.ssh/authorized_keys && chmod 600 /home/fc/.ssh/authorized_keys
install -d -m 755 -o fc -g fc /home/fc/app /home/fc/backups
cat > /etc/sudoers.d/fc <<'SUDO'
fc ALL=(root) NOPASSWD: /usr/sbin/nginx -t, /usr/bin/systemctl reload nginx, /usr/bin/systemctl status nginx
fc ALL=(root) NOPASSWD: /usr/bin/certbot *
fc ALL=(root) NOPASSWD: /usr/bin/install -m 644 -o root -g root /tmp/fungalcharacters.conf /etc/nginx/sites-available/fungalcharacters
fc ALL=(root) NOPASSWD: /usr/bin/ln -sfn /etc/nginx/sites-available/fungalcharacters /etc/nginx/sites-enabled/fungalcharacters
SUDO
chmod 440 /etc/sudoers.d/fc && visudo -cf /etc/sudoers.d/fc
echo "fc ready"
