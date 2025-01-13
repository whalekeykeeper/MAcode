#!/bin/bash
docker compose down -v
docker compose up -d

# Wait for the database to initialize
echo "Waiting for the database to be ready..."
sleep 5

rm -rf alembic/versions/*
alembic revision --autogenerate -m "initial"
alembic upgrade head
