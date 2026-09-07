Manage your Docker Compose stacks and individual containers using these core commands and examples.

**Docker Compose (Stack Management)**

Run these commands from the directory containing your `docker-compose.yml` file:

* **Start the entire stack in the background:**
```bash
docker compose up -d

```


* **Stop and remove containers, networks, and volumes:**
```bash
# Stop containers and remove networks
docker compose down

# Also remove named volumes (cleans up persistent data)
docker compose down -v

```


* **View status of stack containers:**
```bash
docker compose ps

```


* **Stream logs for all or specific services:**
```bash
# All services in the stack
docker compose logs -f

# Specific service (e.g., app)
docker compose logs -f app

```


* **Rebuild and restart updated services:**
```bash
# Pull fresh images and restart in background
docker compose pull && docker compose up -d

# Force rebuild of local Dockerfiles without using cache
docker compose build --no-cache && docker compose up -d

```


* **Execute a command inside a running stack service:**
```bash
# Open interactive shell in 'web' service
docker compose exec web bash

# Run database migration command in 'db' service
docker compose exec db psql -U postgres

```



---

**Docker CLI (Individual Container Management)**

* **List containers:**
```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

```


* **Run a standalone container:**
```bash
# Run Nginx in detached mode, mapping port 8080 to container port 80
docker run -d --name my-web -p 8080:80 nginx:latest

```


* **Control container lifecycle:**
```bash
# Stop a running container
docker stop my-web

# Start a stopped container
docker start my-web

# Restart a container
docker restart my-web

```


* **Stream container logs:**
```bash
# View recent logs and tail new lines
docker logs -f --tail 100 my-web

```


* **Access container shell or execute commands:**
```bash
# Open interactive terminal
docker exec -it my-web /bin/sh

```


* **Monitor resource usage:**
```bash
# Live CPU, memory, network, and I/O metrics
docker stats

```


* **Inspect and clean up:**
```bash
# View low-level IP and configuration data
docker inspect my-web

# Force remove a running container
docker rm -f my-web

# Remove all stopped containers, unused networks, and dangling images
docker system prune -a

```