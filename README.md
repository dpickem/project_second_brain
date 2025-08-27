# Second Brain

A minimal scaffold for a "second brain" application with a Python backend, Neo4j graph database, and React frontend. Knowledge chunks can be ingested via the API and stored in a Neo4j graph for exploration by humans or LLMs.

## Running with Docker Compose

Set a `NEO4J_PASSWORD` (minimum 8 characters) for the Neo4j admin user.
Provide an `OPENAI_API_KEY` if you want embeddings to be generated during ingestion. Then run:

```bash
export NEO4J_PASSWORD=secretsecret
export OPENAI_API_KEY=...
docker compose up --build
```

Both values can be supplied via environment variables or a `.env` file used by Docker Compose.

Services:
- **neo4j** – graph database on ports `7474` (HTTP) and `7687` (bolt)
- **backend** – FastAPI service on `http://localhost:8000`
- **frontend** – React app on `http://localhost:3000`

## Backend API

- `POST /ingest` – JSON body `{ "text": "..." }` creates a `Chunk` node in Neo4j. If `OPENAI_API_KEY` is set, an embedding is stored as well.
- `GET /graph` – returns nodes and relationships for visualisation or further processing.

## Frontend

The React frontend offers a text box to ingest new knowledge and displays the current graph JSON.

This scaffold is ready for further expansion such as advanced graph queries, authentication, or richer visualisations.
