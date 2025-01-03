#!/bin/bash
docker compose down -v
docker compose up -d
rm -rf alembic/versions/*
alembic revision --autogenerate -m "initial"
alembic upgrade head
