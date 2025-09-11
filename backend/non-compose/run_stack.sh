#!/bin/bash
docker compose up -d redis mongo
docker compose run --rm init_proxies
docker compose up -d scraper_worker_0