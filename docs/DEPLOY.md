# Deploying fungalcharacters.org

Server: the shared Hostinger VPS (KVM 2, 85.31.233.192, Ubuntu 24.04) that also runs gulfcoastfungi.com.
nginx, certbot and Docker are already installed there. This site only adds its own pieces; nothing belonging to
other sites is changed.

| Piece | Where |
|---|---|
| Deploy user | `fc` (key-only SSH, limited sudo: nginx test/reload, certbot, installing this site's nginx file) |
| Code | `/home/fc/app/` (copied from the Mac by `deploy/deploy.sh`) |
| Secrets | `/home/fc/app/.env` (only on the server; template `.env.example`) |
| App | Docker: `docker-compose.prod.yml`, gunicorn on `127.0.0.1:8020` (gulfcoastfungi uses 8010) |
| Database | PostgreSQL 17 in Docker, volume `app_pgdata` |
| Web server | nginx block `/etc/nginx/sites-available/fungalcharacters` (copy: `deploy/nginx_fungalcharacters.conf`) |
| Certificate | Let's Encrypt `fungalcharacters.org` (+ www, .com, www.com), webroot `/var/www/html`, auto-renewed |
| Backups | nightly `deploy/backup.sh` → `/home/fc/backups/` (30 days), plus copies pulled to the Mac |
| Email | Resend, sending domain `mail.fungalcharacters.org`, SMTP `smtp.resend.com:465` |
| SSH key (Mac) | `~/.ssh/fungalcharacters_deploy` (comment `fungalcharacters-deploy`) |

## First launch (in order)
1. **Will:** add the public key in hPanel › VPS › SSH keys (it lands in root's keys).
2. **Claude:** run `deploy/server_setup_root.sh` as root (creates `fc`, docker group, folders, limited sudo),
   then remove the key from root and confirm root login with it is refused.
3. **Will:** in hPanel › Domains › DNS for fungalcharacters.org and fungalcharacters.com: A records `@` and `www`
   → 85.31.233.192 (replacing the parking records). For fungalcharacters.org also the four Resend email records
   and the DMARC record.
4. **Claude:** when DNS answers with 85.31.233.192: install `nginx_fungalcharacters_http.conf`, get the certificate
   (`certbot certonly --webroot -w /var/www/html -d fungalcharacters.org -d www.fungalcharacters.org
   -d fungalcharacters.com -d www.fungalcharacters.com`), then install the full `nginx_fungalcharacters.conf`.
5. **Claude:** write `.env` on the server (new secret key and database password; Resend API key created for this
   domain only, sending access), back up the local database, and run
   `deploy/deploy.sh --restore <dump>` so the live site starts from the local database (your review edits included).
6. **Claude:** add the nightly backup to fc's crontab; check pages, email (a real password-reset message),
   two-factor sign-in, certificate, redirects; run the accessibility audit against the live site.
7. **Will:** sign in on the live site and confirm.

## Updates after launch
`deploy/deploy.sh` (copies the code, rebuilds, restarts; migrations run at start). Claude runs it after tests pass.
