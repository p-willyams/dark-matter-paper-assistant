"""
Script para buscar e baixar artigos sobre matéria escura do arXiv.

Requisitos:
    pip install requests feedparser

Uso:
    python baixar_artigos_materia_escura.py

O script busca artigos em diferentes subtemas de matéria escura para
garantir diversidade de conteúdo no seu projeto de RAG, e baixa os PDFs
para a pasta ../data/
"""

import os
import time
import feedparser
import requests

# Pasta onde os PDFs serão salvos
PASTA_SAIDA = os.path.join("..", "data")
os.makedirs(PASTA_SAIDA, exist_ok=True)

BASE_URL = "https://export.arxiv.org/api/query"

# Buscas organizadas por subtema, cada uma com uma quantidade alvo de artigos.
BUSCAS = [
    {
        "nome": "evidencias_observacionais",
        "query": 'abs:"dark matter" AND abs:"rotation curve"',
        "quantidade": 4,
    },
    {
        "nome": "wimp_candidatos_particulas",
        "query": 'abs:"dark matter" AND abs:"WIMP"',
        "quantidade": 4,
    },
    {
        "nome": "cdm_vs_wdm",
        "query": 'abs:"cold dark matter" AND abs:"warm dark matter"',
        "quantidade": 4,
    },
    {
        "nome": "deteccao_experimentos",
        "query": 'abs:"dark matter" AND abs:"direct detection"',
        "quantidade": 4,
    },
    {
        "nome": "reviews_gerais",
        "query": 'abs:"dark matter" AND abs:"review"',
        "quantidade": 4,
    },
]


def buscar_artigos(query, quantidade, ordenar_por="relevance"):
    """Consulta a API do arXiv e retorna uma lista de entradas (metadados)."""
    params = {
        "search_query": query,
        "start": 0,
        "max_results": quantidade,
        "sortBy": ordenar_por,  # relevance ou submittedDate
        "sortOrder": "descending",
    }
    resposta = requests.get(BASE_URL, params=params, timeout=30)
    resposta.raise_for_status()
    feed = feedparser.parse(resposta.text)
    return feed.entries


def baixar_pdf(entry, pasta_destino):
    """Baixa o PDF de uma entrada do arXiv."""
    arxiv_id = entry.id.split("/abs/")[-1]
    pdf_url = entry.id.replace("/abs/", "/pdf/")
    if not pdf_url.endswith(".pdf"):
        pdf_url += ".pdf"

    nome_arquivo = arxiv_id.replace("/", "_") + ".pdf"
    caminho = os.path.join(pasta_destino, nome_arquivo)

    if os.path.exists(caminho):
        print(f"  [já existe] {nome_arquivo}")
        return caminho

    resposta = requests.get(pdf_url, timeout=60)
    resposta.raise_for_status()
    with open(caminho, "wb") as f:
        f.write(resposta.content)

    print(f"  [baixado] {nome_arquivo} — {entry.title.strip()[:70]}")
    return caminho


def main():
    log = []
    total_baixado = 0

    for busca in BUSCAS:
        print(f"\nBuscando subtema: {busca['nome']} ({busca['quantidade']} artigos)")
        entradas = buscar_artigos(busca["query"], busca["quantidade"])

        if not entradas:
            print("  Nenhum resultado encontrado para essa query.")
            continue

        for entry in entradas:
            try:
                caminho = baixar_pdf(entry, PASTA_SAIDA)
                log.append(
                    {
                        "subtema": busca["nome"],
                        "titulo": entry.title.strip(),
                        "autores": ", ".join(a.name for a in entry.authors),
                        "publicado": entry.published,
                        "arquivo": caminho,
                        "resumo": entry.summary.strip().replace("\n", " "),
                    }
                )
                total_baixado += 1
                time.sleep(1)  # respeita o rate limit do arXiv
            except Exception as e:
                print(f"  [erro] Falha ao baixar artigo: {e}")

    # Salva um índice com metadados de tudo que foi baixado.
    import json

    with open(os.path.join(PASTA_SAIDA, "_indice.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\nConcluído. {total_baixado} artigos baixados em ./{PASTA_SAIDA}/")
    print("Índice de metadados salvo em _indice.json")


if __name__ == "__main__":
    main()
