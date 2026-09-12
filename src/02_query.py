# %%

import os
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
import dotenv

dotenv.load_dotenv()
import qdrant_client
from qdrant_client import models
from openai import OpenAI

QDRANT_CLUSTER_URL = os.getenv("QDRANT_CLUSTER_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

DENSE_MODEL = "BAAI/bge-base-en-v1.5"
SPARSE_MODEL = "Qdrant/BM25"
COLBERT_MODEL = "colbert-ir/colbertv2.0"

client_qdrant = qdrant_client.QdrantClient(
    api_key=QDRANT_API_KEY, url=QDRANT_CLUSTER_URL
)
client_openai = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

dense_embedding = TextEmbedding(DENSE_MODEL)
sparse_embedding = SparseTextEmbedding(SPARSE_MODEL)
colbert_embedding = LateInteractionTextEmbedding(COLBERT_MODEL)


def format_pages(pages):
    if not pages:
        return "page not identified"
    if len(pages) == 1:
        return f"p. {pages[0]}"
    return f"pp. {pages[0]}–{pages[-1]}"


def build_context(results):
    blocks = []
    for i, r in enumerate(results.points):
        meta = r.payload.get("metadata", {})
        title = meta.get("title") or "Unknown title"
        authors = meta.get("authors") or "Unknown authors"
        year = meta.get("year") or "Unknown year"
        pages = format_pages(meta.get("pages", []))

        citation = f"{title} — {authors} ({year}), {pages}"

        block = f"[Document {i + 1}]\nSource: {citation}\nExcerpt:\n{r.payload['text']}"
        blocks.append(block)

    return "\n\n---\n\n".join(blocks)


SYSTEM_PROMPT = """
You are an assistant specialized in answering questions using retrieved documents
from scientific papers.

Each retrieved document contains a "Source" line with its citation metadata:
title, authors, year, and page. Use this metadata to cite the information you use.

Rules:

1. Answer the user's question using ONLY the information provided in the context.

2. Do not use external knowledge. Do not invent facts, numbers, explanations,
   sources, page numbers, authors, titles, or conclusions.

3. Every factual claim supported by a retrieved document must have an inline
   citation immediately after the claim.

4. Use the exact citation information provided in the "Source" line.
   Do not modify, complete, or infer missing metadata.

5. If the page number is available, cite it.
   If the page number is not available, do not invent one.

6. If multiple documents directly support the same claim, cite all relevant
   documents.

7. Only cite documents that actually support the claim being made.
   Do not cite a document simply because it is related to the topic.

8. If the context does not contain enough information to answer the question,
   say so clearly. Do not guess or use outside knowledge.

9. Distinguish between established results, observations, interpretations,
   assumptions, and hypotheses. Do not present an interpretation or hypothesis
   as an established fact.

10. Answer directly and concisely.

11. Preserve scientific and technical terminology accurately.

12. At the end of the answer, include a "References" section containing ONLY
    the sources actually cited in the answer.

13. In the References section, use ONLY the title, authors, and year.
Do not include page numbers in the References section.
Use exactly this format:
- Title — Authors (Year)

14. Do not add explanations such as "provides context" or "not specific evidence"
    to the References section.

Citation format:
Use:
(Source title, Authors, Year, p. X)

Example:
(The Nature of the Dark Matter, Kim Griest, 1995, p. 2)

If metadata is missing, preserve the missing field exactly as provided instead
of guessing.
"""

while True:
    query = input("Enter your question: ")

    dense_query = list(dense_embedding.passage_embed(query))[0].tolist()
    sparse_query = list(sparse_embedding.passage_embed(query))[0].as_object()
    colbert_query = list(colbert_embedding.passage_embed(query))[0].tolist()

    results = client_qdrant.query_points(
        collection_name="DarkRag",
        prefetch={
            "prefetch": [
                {"query": dense_query, "using": "dense", "limit": 20},
                {"query": sparse_query, "using": "sparse", "limit": 20},
            ],
            "query": models.FusionQuery(fusion=models.Fusion.RRF),
            "limit": 20,
        },
        query=colbert_query,
        using="colbert",
        limit=3,
    )

    context = build_context(results)

    user_prompt = f"""
    Context:
    {context}

    Question:
    {query}
    """

    response = client_openai.responses.create(
        model="openai/gpt-oss-20b",
        instructions=SYSTEM_PROMPT,
        input=user_prompt,
    )

    print("\n" + "=" * 40 + "\n")
    print(response.output_text)
    print("\n" + "=" * 40 + "\n")
