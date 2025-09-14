# 🐳 Docker Compose Cheat Sheet (Word-Graph Setup)

## 🔨 Build
- Build all services (use cache if possible):
```bash
docker compose build
```
- Build without cache (fresh layers):
```bash
docker compose build --no-cache
```
- Build a single service (e.g. API only):
```bash
docker compose build api
```

---

## 🚀 Run / Start
- Start everything in background:
```bash
docker compose up -d
```
- Start + rebuild:
```bash
docker compose up -d --build
```
- Start one service:
```bash
docker compose up -d api
```

---

## 🛑 Stop / Remove
- Stop containers (keeps volumes + network):
```bash
docker compose down
```
- Stop + remove volumes (⚠ wipes DB data):
```bash
docker compose down -v
```
- Stop one service:
```bash
docker compose stop api
```

---

## 📜 Logs
- Tail all logs:
```bash
docker compose logs -f
```
- Tail specific service:
```bash
docker compose logs -f api
docker compose logs -f worker_0
```

---

## 🔎 Inspect / Debug
- List running containers:
```bash
docker ps
```
- Check container health/status:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
- Exec into a container shell:
```bash
docker exec -it api bash
```
- Check open ports:
```bash
ss -ltnp | grep 3001
```

---

## 📦 Volumes
- List all volumes:
```bash
docker volume ls
```
- Inspect a specific volume:
```bash
docker volume inspect scraper-system_mongo_data
```

---

## 🧹 Cleanup
- Remove stopped containers:
```bash
docker container prune
```
- Remove unused images:
```bash
docker image prune
```
- Remove unused volumes (⚠ wipes data):
```bash
docker volume prune
```

---

⚡ **Workflow tip**  
- Dev API changes → `docker compose up -d --build api`  
- Big config change → `docker compose up -d --build`  
- Safe stop → `docker compose down`  
- Nuclear reset → `docker compose down -v && docker volume prune`
