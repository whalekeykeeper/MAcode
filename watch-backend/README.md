# Backend for MA thesis

## Thesis topic

Turning Videos into AI-enhanced Learning Opportunities: Applying Distributional Semantics into Incidental Vocabulary
Learning

## Requirements

- Python 3.11

## Version Control

- Poetry is used to manage dependencies. To install the dependencies, run the following command:

```bash
poetry install
```

- Set up in PyCharm to use Poetry as the project interpreter or use command:

```bash
poetry shell
```

## Description

## Initiate the project for the first time

1. Run docker compose to start the database:

```bash
docker compose up -d
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

Whenever changed the data model, run a shell script to generate a new migration:

```bash
./reset_db.sh
```

## Test

```bash
pytest
```

## Get videos in a batch for experiment from the root directory

```
poetry run python -m tools.batch_inject_videos
```

## Project Structure


