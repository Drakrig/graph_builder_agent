# Graph Builder Agent

This repository contains the example code of a Graph Building Agent designed to extract structured knowledge from markdown documents and integrate it into a graph database (Neo4j/Memgraph) and a vector database (Weaviate). The agent utilizes Large Language Models (LLMs) via LangChain and LangGraph to analyze text, extract entities (nodes), infer relationships, and enrich knowledge iteratively.

## Status

Currently, only the euristic-based extraction is implemented. The true Agent-based with tool calling is planned for future development, even so the current implementation already demonstrates the core concepts. 

## Features

- **Node Extraction:** Identifies entities such as characters, locations, organizations etc. from markdown files.
- **Relationship Extraction:** Infers relationships between nodes using document content and existing graph relationships.
- **Schema Validation:** Enforces strict JSON structures for nodes and relationships, ensuring compatibility with downstream systems.
- **Knowledge Graph Integration:** Creates, updates, and merges nodes and relationships in a graph database (Memgraph/Neo4j).
- **Vector Database Augmentation:** Inserts and searches entity information in Weaviate for enhanced context retrieval.
- **LLM-powered Enrichment:** Uses LLMs (Ollama via LangChain) to merge, compare, and enrich node and relationship descriptions.

## Installation

Clone the repository and install the dependencies listed in your project's requirements.

```bash
git clone https://github.com/Drakrig/graph_builder_agent.git
cd graph_builder_agent
# Install dependencies, e.g.:
pip install -r requirements.txt
```

Set up your `.env` file with credentials for Memgraph/Neo4j and Weaviate.

## Presequences

- A running instance of Weaviate or Neo4j (initial data not required but recommended unless you want to start from complete scratch).
- A running instance of Memgraph.
- An LLM accessible via LangChain (e.g., Ollama, vLLM, etc.).
- .env file with connection details and credentials. Check the "Environment Variables" section below for required variables.

## Usage

Check provided notebooks for examples of:
 - how to build the graph and use it;
 - how to populate the vector database and use it for context search.
 - how to populate the graph database with initial data.

### Core Modules

- `functionality/agent.py`: Main orchestration logic for the agent's workflow, including state management, node/relationship extraction, schema validation, and LLM calls.
- `functionality/states.py`: TypedDict definitions for agent states, nodes, relationships, and schemas for validation.
- `functionality/prompts.py`: LLM prompt templates for node and relationship extraction/comparison/enrichment.
- `functionality/graphs.py`: Functions for interacting with the graph database (querying, creating, updating nodes and relationships).
- `functionality/cypher_queries.py`: Cypher query templates for graph operations.
- `functionality/llm_calls.py`: LLM utility functions for merging and comparing nodes/descriptions.
- `functionality/vector_database.py`: Integration with Weaviate for node insertions and similarity searches.

## Environment Variables

Configure the following in `.env`:

```
MEMGRAPH_URI=bolt://localhost:7687
MEMGRAPH_USER=your_user
MEMGRAPH_PASSWORD=your_password
WEAVIATE_HTTP_HOST=localhost
WEAVIATE_HTTP_PORT=8080
WEAVIATE_HTTP_SECURE=false
WEAVIATE_GRPC_HOST=localhost
WEAVIATE_GRPC_PORT=8081
WEAVIATE_GRPC_SECURE=false
LOG_LEVEL=DEBUG
```

## Extending

- **Prompts:** Custom prompts for LLMs can be added/modified in `prompts.py`.
- **Schemas:** Node/relationship schemas and validation logic are in `states.py`.
- **Database Backends:** The code supports Memgraph/Neo4j and Weaviate; adapt connection logic as needed.

## Roadmap

Planned features include:
- Full Agent-based implementation with tool calling.
- More flexible swithching in Weaviate collections and tenants (currently hardcoded).
- Add MCP server for Agent.

## License

MIT License (see LICENSE file).

## Acknowledgments

Built on LangChain, LangGraph, Neo4j/Memgraph, Weaviate, and Ollama.