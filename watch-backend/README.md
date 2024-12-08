# Backend for MA thesis

## Thesis topic
Turning Videos into AI-enhanced Learning Opportunities: Applying Distributional Semantics into Incidental Vocabulary Learning


## Requirements
- Python 3.11

## Version Control
- Poetry is used to manage dependencies. To install the dependencies, run the following command:
```bash
poetry install
```
- Set up in PyCharm to use Poetry as the project interpreter.


## Description

## Initiate the project for the first time
1. Run docker compose to start the database:
```bash
docker-compose up -d
```
2. Run the app:
```bash
uvicorn main:app --reload
```
3. Run `init.sh` to create the database and tables.
```bash
./init.sh
```

4. Run alembic migrations:
```bash
alembic upgrade head
```

## Run the app for development
- Use bash commands or click on the run button in the IDE.
```bash
uvicorn main:app --reload
```

Whenever changed the data model, run the following command to generate a new migration:
```bash
alembic revision --autogenerate -m "migration message"
alemibc upgrade head
```

## Test
```bash
pytest
```

