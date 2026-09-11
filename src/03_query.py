import os
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
import dotenv

dotenv.load_dotenv()
import qdrant_client
from qdrant_client import models


QDRANT_CLUSTER_URL = os.getenv("QDRANT_CLUSTER_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

DENSE_MODEL = "BAAI/bge-base-en-v1.5"
SPARSE_MODEL = "Qdrant/BM25"
COLBERT_MODEL = "colbert-ir/colbertv2.0"

client = qdrant_client.QdrantClient(api_key=QDRANT_API_KEY, url=QDRANT_CLUSTER_URL)

dense_embedding = TextEmbedding(DENSE_MODEL)
sparse_embedding = SparseTextEmbedding(SPARSE_MODEL)
colbert_embedding = LateInteractionTextEmbedding(COLBERT_MODEL)

while True:
    query = input("Enter your question: ")

    dense_query = list(dense_embedding.passage_embed(query))[0].tolist()
    sparse_query = list(sparse_embedding.passage_embed(query))[0].as_object()
    colbert_query = list(colbert_embedding.passage_embed(query))[0].tolist()

    results = client.query_points(
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

    for r in results.points:
        print("=" * 50)
        print(r.payload["text"])
        print("=" * 50)
        print()
