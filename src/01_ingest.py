# %%
import os
import json
import uuid
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from transformers import AutoTokenizer
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
import dotenv
from tqdm import tqdm

dotenv.load_dotenv()
import qdrant_client
from qdrant_client import models

QDRANT_CLUSTER_URL = os.getenv("QDRANT_CLUSTER_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

DENSE_MODEL = "BAAI/bge-base-en-v1.5"
SPARSE_MODEL = "Qdrant/BM25"
COLBERT_MODEL = "colbert-ir/colbertv2.0"

client = qdrant_client.QdrantClient(api_key=QDRANT_API_KEY, url=QDRANT_CLUSTER_URL)

collections = [c.name for c in client.get_collections().collections]

if "DarkRag" not in collections:
    client.create_collection(
        collection_name="DarkRag",
        vectors_config={
            "dense": models.VectorParams(size=768, distance=models.Distance.COSINE),
            "colbert": models.VectorParams(
                size=128,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
            ),
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )


def load_metadata_index(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    index = {}
    for r in records:
        file_name = os.path.basename(r["arquivo"])
        index[file_name] = {
            "title": r.get("titulo"),
            "authors": r.get("autores"),
            "year": r.get("publicado", "")[:4],
            "subtopic": r.get("subtema"),
        }
    return index


def extract_pages(chunk):
    pages = set()
    for item in getattr(chunk.meta, "doc_items", []) or []:
        for prov in getattr(item, "prov", []) or []:
            page = getattr(prov, "page_no", None)
            if page is not None:
                pages.add(page)
    return sorted(pages)


def doc_to_vectordb(path, metadata_index):
    file_name = os.path.basename(path)
    article_metadata = metadata_index.get(file_name, {})

    if not article_metadata:
        print(f"  ⚠ No metadata found in the index for {file_name}")

    doc_converter = DocumentConverter()
    doc = doc_converter.convert(path)

    tokenizer = AutoTokenizer.from_pretrained(DENSE_MODEL)

    chunker = HybridChunker(tokenizer=tokenizer, max_tokens=512)

    dense_embedding = TextEmbedding(DENSE_MODEL)
    sparse_embedding = SparseTextEmbedding(SPARSE_MODEL)
    colbert_embedding = LateInteractionTextEmbedding(COLBERT_MODEL)

    chunks = list(chunker.chunk(doc.document))

    points = []

    for i, c in enumerate(chunks):
        token_count = len(
            tokenizer(c.text, add_special_tokens=True, truncation=False)["input_ids"]
        )

        if token_count > 512:
            continue

        dense_vector = list(dense_embedding.passage_embed(c.text))[0].tolist()
        sparse_vector = list(sparse_embedding.passage_embed(c.text))[0].as_object()
        colbert_vector = list(colbert_embedding.passage_embed(c.text))[0].tolist()

        pages = extract_pages(c)

        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector={
                "dense": dense_vector,
                "sparse": sparse_vector,
                "colbert": colbert_vector,
            },
            payload={
                "text": c.text,
                "metadata": {
                    "file_name": file_name,
                    "title": article_metadata.get("title"),
                    "authors": article_metadata.get("authors"),
                    "year": article_metadata.get("year"),
                    "subtopic": article_metadata.get("subtopic"),
                    "pages": pages,
                },
            },
        )

        points.append(point)

        if len(points) >= 32:
            client.upload_points(
                collection_name="DarkRag",
                points=points,
                batch_size=5,
                parallel=1,
                max_retries=3,
            )
            points = []

    if points:
        client.upload_points(
            collection_name="DarkRag",
            points=points,
            batch_size=5,
            parallel=1,
            max_retries=3,
        )

    print("Upload completed!")


data_dir = os.path.join("../data")
index_path = os.path.join(data_dir, "_indice.json")

metadata_index = load_metadata_index(index_path)

file_list = [
    os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".pdf")
]

for file_path in tqdm(file_list):
    doc_to_vectordb(file_path, metadata_index)

# %%
