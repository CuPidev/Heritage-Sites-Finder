## Auto-deploy to your VPS (GitHub Actions)

This project includes a GitHub Actions workflow that can automatically deploy the repository to a Linux VPS (Ubuntu) whenever you push to `main`.

What the workflow does

-   rsyncs repository files to your remote path (excludes `.git`, `.venv`, and `data/`)
-   connects to the VPS via SSH and ensures a Python venv exists
-   installs requirements
-   restarts the `heritage` systemd service (you must have created this service on the server)

Secrets you must configure in the GitHub repo (Repository > Settings > Secrets and variables > Actions):

-   `DEPLOY_HOST` — the hostname or IP of your VPS (e.g. `1.2.3.4`)
-   `DEPLOY_USER` — remote user (e.g. `deploy`)
-   `DEPLOY_PATH` — absolute path on remote where repo should be deployed (e.g. `/srv/heritage`)
-   `DEPLOY_SSH_KEY` — the private SSH key for `DEPLOY_USER` in PEM format. The public key must be placed in `~/.ssh/authorized_keys` for the deploy user.

Server setup reminders

-   Create a `deploy` user and give it ownership of the `DEPLOY_PATH`.
-   Either grant the user passwordless sudo for `systemctl restart heritage` or configure a different restart strategy (e.g., a supervisor that the user can control).
-   Ensure `rsync` and `python3-venv` are installed on the server.

Example steps to prepare the server (run as root or sudo):

```
adduser deploy
mkdir -p /srv/heritage
chown deploy:deploy /srv/heritage
apt update && apt install -y rsync python3-venv python3-pip
# allow deploy to restart the service without password (use with caution)
echo "deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart heritage" > /etc/sudoers.d/deploy-heritage
chmod 440 /etc/sudoers.d/deploy-heritage
```

Manual deploy option
If you prefer to deploy from your machine instead of GitHub Actions, use the helper script:

```
./scripts/deploy_vps.sh deploy@1.2.3.4 /srv/heritage
```

This will rsync files and run the same venv/setup commands on the remote host.

Notes & security

-   The workflow excludes `data/` from rsync to avoid overwriting any site-specific data (you can include it if you want). If you need to upload a prebuilt `data/index.pkl`, scp it separately.
-   Keep your private SSH key secret. Rotate it if you suspect compromise.
-   For high-availability or zero-downtime deployment, consider a more advanced process (rolling update, blue/green deploy, load balancer).

Need help
If you want, I can also:

-   add a Dockerfile and docker-compose setup for containerized deployment
-   make the workflow build an index artifact and rsync it to the server
-   switch `src/feedback.py` to use SQLite for safe concurrent ingestion on the server
