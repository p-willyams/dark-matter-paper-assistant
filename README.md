# DarkRag

*Leia em [Português](README.pt-br.md).*

DarkRag is a Retrieval-Augmented Generation (RAG) system for exploring scientific literature on **dark matter**. It ingests scientific papers from arXiv, indexes them using a hybrid retrieval strategy, and answers natural-language questions with citations pointing back to the exact paper, page, authors, and year the information came from.

This project was built as a hands-on learning exercise to go through the full lifecycle of a RAG application: data ingestion, chunking, hybrid retrieval, guardrails, an API layer, a UI, and containerization, rather than to serve as a production deployment. It is not currently deployed publicly.

## Overview

Given a question like *"What evidence supports the existence of dark matter?"*, DarkRag:

1. Classifies whether the question is within the scope of the indexed dataset
2. Retrieves the most relevant passages from the paper collection using a combination of dense, sparse (keyword), and late-interaction (ColBERT) search
3. Sends the retrieved passages to an LLM, instructed to answer **only** from that context
4. Returns an answer with inline citations (title, authors, year, page) and a references section
5. Flags any citation in the answer that doesn't match a real source in the retrieved context

> <img width="1130" height="848" alt="image" src="https://github.com/user-attachments/assets/81bf346b-3743-483d-9fa6-33cae85ae005" />



## How it was built

| Stage | What it does | Key tools |
|---|---|---|
| Data collection | Searches and downloads papers from arXiv across multiple dark matter subtopics (observational evidence, particle candidates, CDM vs. WDM, detection experiments, reviews) | arXiv API |
| Parsing & chunking | Converts PDFs directly (not pre-extracted text) into structured chunks, preserving page-level provenance | [Docling](https://github.com/docling-project/docling) `HybridChunker` |
| Embeddings | Generates three complementary vector representations per chunk | `BAAI/bge-base-en-v1.5` (dense), `Qdrant/BM25` (sparse), `colbert-ir/colbertv2.0` (late interaction), via [FastEmbed](https://github.com/qdrant/fastembed) |
| Vector storage | Stores all three vector types per point, enabling hybrid search | [Qdrant Cloud](https://cloud.qdrant.io) |
| Retrieval | Prefetches with dense + sparse search, fuses results (RRF), then reranks with ColBERT for precision | Qdrant `query_points` |
| Guardrails | Classifies out-of-scope questions before retrieval; verifies that citations in the generated answer match real sources in the retrieved context | Custom LLM-based classifier + regex-based citation check |
| Generation | Answers strictly from retrieved context, with mandatory inline citations and a references section | LLM via Groq (`openai/gpt-oss-20b`) |
| API | Exposes the pipeline as a REST endpoint | FastAPI |
| Frontend | Chat interface consuming the API | Streamlit |
| Packaging | Two containers (API + frontend) orchestrated together | Docker, Docker Compose |

### Why a hybrid retrieval strategy?

Scientific papers mix precise technical terms (model names, particle names, exact figures) with conceptual language. Dense embeddings capture semantic meaning and paraphrasing well but can miss exact terms; sparse (BM25) search captures exact keyword matches but misses synonyms; ColBERT's token-level late interaction adds a more precise reranking pass on top of both. Combining the three balances recall and precision better than any single method alone.

### Why guardrails?

Two failure modes are common in RAG systems: answering questions the dataset has no business answering, and citing sources that don't actually support a claim (or don't exist at all). DarkRag addresses both with a lightweight LLM-based scope classifier (run before the expensive retrieval + generation steps) and a citation-checking pass after generation, which cross-references every citation the model produced against the titles that were actually retrieved.

## Results

- Indexed **20 papers** across 5 dark matter subtopics
- Answers include inline citations resolved down to **title, authors, year, and page number**
- Out-of-scope questions (e.g., unrelated topics) are detected and rejected before wasting a retrieval/generation call
- Citations not grounded in the retrieved context are flagged in the response rather than silently presented as fact

> <img width="1066" height="843" alt="image" src="https://github.com/user-attachments/assets/8037183f-b7cd-436f-8042-adb10dc9663c" />



## Project structure

```
DarkRag/
├── data/                       # _indice.json (paper metadata) + downloaded PDFs
├── scripts/
│   └── download_papers.py      # searches and downloads papers from arXiv
├── src/
│   ├── backend/
│   │   ├── ingest.py            # chunks, embeds, and indexes papers into Qdrant
│   │   ├── query.py             # retrieval + generation pipeline
│   │   ├── guardrails.py        # scope classification + citation verification
│   │   ├── api.py               # FastAPI app
│   │   └── Dockerfile
│   └── frontend/
│       ├── app.py               # Streamlit chat interface
│       └── Dockerfile
├── docker-compose.yml
├── requirements-backend.txt
├── requirements-frontend.txt
├── .env.example
└── README.md
```

## Running the project

### Prerequisites

- Python 3.11+ (if running without Docker)
- Docker and Docker Compose (recommended)
- A [Qdrant Cloud](https://cloud.qdrant.io) cluster (free tier is enough)
- A [Groq](https://console.groq.com) API key

### 1. Configure environment variables

Copy the example file and fill in your own credentials:

```bash
cp .env.example .env
```

### 2. Download the papers

```bash
cd scripts
python download_papers.py
```

This downloads PDFs into `data/` along with an `_indice.json` metadata file.

### 3. Index the papers into Qdrant

From inside `src/`:

```bash
pip install -r ../requirements-backend.txt docling transformers tqdm
cd src
python backend/ingest.py
```

(`ingest.py` needs `docling` and `transformers`, which aren't in `requirements-backend.txt` on purpose — they're only needed for this one-off indexing step, not for the deployed API.)

### 4. Run with Docker Compose (recommended)

From the project root:

```bash
docker compose up --build
```

- API: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- Frontend: [http://localhost:8501](http://localhost:8501)

### 4b. Or run locally without Docker

```bash
# Terminal 1 — API
pip install -r requirements-backend.txt
uvicorn src.backend.api:app --reload

# Terminal 2 — Frontend
pip install -r requirements-frontend.txt
streamlit run src/frontend/app.py
```

## Known limitations

- No authentication on the API — acceptable for a local/portfolio project, but would need an API key or similar before any public deployment
- The out-of-scope classifier is LLM-based and heuristic; it can occasionally misclassify ambiguous questions
- Citation verification uses substring matching on titles, which can produce false positives/negatives on heavily paraphrased citations
- Not deployed publicly — intended to be run locally as a demonstration of the full RAG lifecycle

## License

MIT — see [LICENSE](LICENSE).
