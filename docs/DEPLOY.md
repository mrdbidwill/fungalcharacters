# Deploying fungalcharacters.org

Server: the shared Hostinger VPS (KVM 2, 85.31.233.192, Ubuntu 24.04) that also runs gulfcoastfungi.com.
nginx, certbot and Docker are already installed there. This site only adds its own pieces; nothing belonging to
other sites is changed.

| Piece | Where |
|---|---|
| Deploy user | set up by the Website Administrator (assumed `fc`, key-only SSH, in the docker group) |
| Code | `/home/fc/app/` (copied from the Mac by `deploy/deploy.sh`) |
| Secrets | `/home/fc/app/.env` (only on the server; template `.env.example`) |
| App | Docker: `docker-compose.prod.yml`, gunicorn on `127.0.0.1:8030` (gulfcoastfungi uses 8010, mrdbid.com 8020) |
| Database | PostgreSQL 17 in Docker, Compose project `fungalcharacters`, volume `fungalcharacters_pgdata` |
| Web server | nginx, set up by the Website Administrator (proposed block: `deploy/nginx_fungalcharacters.conf`) |
| Certificate | Let's Encrypt for fungalcharacters.org, www, .com, www.com — Website Administrator |
| Backups | nightly `deploy/backup.sh` → `/home/fc/backups/` (30 days), plus copies pulled to the Mac |
| Email | Resend, sending domain `mail.fungalcharacters.org`, SMTP `smtp.resend.com:465` |
| SSH key (Mac) | `~/.ssh/fungalcharacters_deploy` (comment `fungalcharacters-deploy`) |

## Who does what (2026-11-25)
- **Website Administrator project:** server setup (deploy user, docker group, folders), nginx, DNS and the
  certificate. Its input from this project: the proposed nginx block `deploy/nginx_fungalcharacters.conf`
  (app on 127.0.0.1:8030; 8020 is the live mrdbid.com app) and the table above.
- **This project (Claude in VS Code):** deploys the app after that, with `deploy/deploy.sh`.

## First launch (after the Website Administrator's setup)
1. Confirm with the Website Administrator: deploy user and folders (assumed `fc`, `/home/fc/app`,
   `/home/fc/backups`), and the SSH key to use (assumed `~/.ssh/fungalcharacters_deploy`). Adjust `deploy/deploy.sh`
   and `deploy/backup.sh` if they differ.
2. Write `.env` on the server (new secret key and database password; a Resend API key created for this domain only,
   sending access), back up the local database, and run `deploy/deploy.sh --restore <dump>` so the live site
   starts from the local database (Will's review edits included).
3. Add the nightly backup to the deploy user's crontab.
4. Check: pages, email (a real password-reset message), two-factor sign-in, the accessibility audit against the live
   site. Then Will signs in and confirms.

## Updates after launch
`deploy/deploy.sh` (copies the code, rebuilds, restarts; migrations run at start). Claude runs it after tests pass.
