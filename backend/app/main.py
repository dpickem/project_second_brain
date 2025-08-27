from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase
import os
import openai

app = FastAPI(title="Second Brain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "secret")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


class IngestRequest(BaseModel):
    text: str


@app.post("/ingest")
async def ingest(data: IngestRequest):
    embedding = None
    if OPENAI_API_KEY:
        response = await openai.Embedding.acreate(
            model="text-embedding-3-small",
            input=data.text,
        )
        embedding = response["data"][0]["embedding"]
    with _driver.session() as session:
        session.run(
            "CREATE (c:Chunk {content: $content, embedding: $embedding})",
            content=data.text,
            embedding=embedding,
        )
    return {"status": "ok"}


@app.get("/graph")
async def graph():
    with _driver.session() as session:
        result = session.run("MATCH (n)-[r]->(m) RETURN n,r,m")
        nodes = []
        rels = []
        seen = set()
        for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]
            if n.id not in seen:
                nodes.append({"id": n.id, "labels": list(n.labels), **dict(n)})
                seen.add(n.id)
            if m.id not in seen:
                nodes.append({"id": m.id, "labels": list(m.labels), **dict(m)})
                seen.add(m.id)
            rels.append({
                "start": r.start_node.id,
                "end": r.end_node.id,
                "type": r.type,
            })
    return {"nodes": nodes, "relationships": rels}


@app.get("/")
async def root():
    return {"message": "Second Brain API"}
