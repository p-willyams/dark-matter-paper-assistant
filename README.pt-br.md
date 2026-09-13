<img width="1920" height="1080" alt="dark-assistant" src="https://github.com/user-attachments/assets/61cc3296-1eda-4a9e-91e9-edad57d4d2e0" />

*Leia em [English](README.md).*

DarkRag é um sistema de **Retrieval-Augmented Generation (RAG)** para explorar literatura científica sobre **matéria escura**. O sistema coleta artigos científicos do arXiv, indexa os documentos utilizando uma estratégia de recuperação híbrida e responde a perguntas em linguagem natural com citações que apontam para o artigo, página, autores e ano exatos de onde as informações foram obtidas.

Este projeto foi desenvolvido como um exercício prático de aprendizado, percorrendo todo o ciclo de desenvolvimento de uma aplicação RAG: ingestão de dados, divisão em chunks, recuperação híbrida, guardrails, camada de API, interface de usuário e conteinerização. O objetivo não é servir como uma aplicação em produção. Atualmente, o projeto não está disponível publicamente.

## Visão geral

Dada uma pergunta como *"Quais evidências sustentam a existência da matéria escura?"*, o DarkRag:

1. Classifica se a pergunta está dentro do escopo do conjunto de dados indexado
2. Recupera os trechos mais relevantes da coleção de artigos utilizando uma combinação de busca densa, esparsa (palavras-chave) e de interação tardia (ColBERT)
3. Envia os trechos recuperados para um LLM, instruído a responder **somente** com base nesse contexto
4. Retorna uma resposta com citações inline (título, autores, ano e página) e uma seção de referências
5. Identifica qualquer citação presente na resposta que não corresponda a uma fonte real encontrada no contexto recuperado

> <img width="1130" height="848" alt="image" src="https://github.com/user-attachments/assets/445fa9ce-ab3e-4707-9da6-a3c10f347354" />




## Como foi construído

| Etapa                  | O que faz                                                                                                                                                                                      | Principais ferramentas                                                                                                                                      |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coleta de dados        | Pesquisa e baixa artigos do arXiv sobre diferentes subtemas de matéria escura (evidências observacionais, candidatos a partículas, CDM vs. WDM, experimentos de detecção e artigos de revisão) | API do arXiv                                                                                                                                                |
| Parsing e chunking     | Converte PDFs diretamente (sem depender de texto previamente extraído) em chunks estruturados, preservando a procedência em nível de página                                                    | [Docling](https://github.com/docling-project/docling) `HybridChunker`                                                                                       |
| Embeddings             | Gera três representações vetoriais complementares para cada chunk                                                                                                                              | `BAAI/bge-base-en-v1.5` (denso), `Qdrant/BM25` (esparso), `colbert-ir/colbertv2.0` (interação tardia), via [FastEmbed](https://github.com/qdrant/fastembed) |
| Armazenamento vetorial | Armazena os três tipos de vetores em cada ponto, permitindo a realização de buscas híbridas                                                                                                    | [Qdrant Cloud](https://cloud.qdrant.io)                                                                                                                     |
| Recuperação            | Faz prefetch utilizando busca densa + esparsa, combina os resultados (RRF) e depois realiza reranking com ColBERT para aumentar a precisão                                                     | Qdrant `query_points`                                                                                                                                       |
| Guardrails             | Classifica perguntas fora do escopo antes da recuperação e verifica se as citações geradas correspondem a fontes reais presentes no contexto recuperado                                        | Classificador baseado em LLM + verificação de citações com regex                                                                                            |
| Geração                | Responde estritamente com base no contexto recuperado, utilizando citações inline obrigatórias e uma seção de referências                                                                      | LLM via Groq (`openai/gpt-oss-20b`)                                                                                                                         |
| API                    | Disponibiliza o pipeline por meio de um endpoint REST                                                                                                                                          | FastAPI                                                                                                                                                     |
| Frontend               | Interface de chat que consome a API                                                                                                                                                            | Streamlit                                                                                                                                                   |
| Empacotamento          | Dois containers (API + frontend) orquestrados em conjunto                                                                                                                                      | Docker, Docker Compose                                                                                                                                      |

### Por que utilizar uma estratégia de recuperação híbrida?

Artigos científicos combinam termos técnicos precisos — como nomes de modelos, partículas e valores exatos — com linguagem conceitual. Embeddings densos capturam bem o significado semântico e paráfrases, mas podem não identificar alguns termos exatos. A busca esparsa (BM25) captura correspondências exatas de palavras-chave, mas pode ter dificuldade com sinônimos. O ColBERT, por meio de sua interação tardia em nível de token, adiciona uma etapa de reranking mais precisa sobre os resultados das duas abordagens.

A combinação das três estratégias proporciona um melhor equilíbrio entre **recall e precisão** do que a utilização de qualquer uma delas isoladamente.

### Por que utilizar guardrails?

Dois modos de falha são comuns em sistemas RAG: responder perguntas que o conjunto de dados não possui informações suficientes para responder e citar fontes que não sustentam realmente uma afirmação — ou que sequer existem.

O DarkRag aborda esses dois problemas com:

* um classificador leve baseado em LLM para verificar o escopo da pergunta antes das etapas mais custosas de recuperação e geração;
* uma etapa de verificação de citações após a geração, que compara cada citação produzida pelo modelo com os títulos das fontes que realmente foram recuperadas.

## Resultados

* **20 artigos indexados** distribuídos entre 5 subtemas relacionados à matéria escura
* As respostas incluem citações inline resolvidas até **título, autores, ano e número da página**
* Perguntas fora do escopo — por exemplo, perguntas sobre assuntos não relacionados — são detectadas e rejeitadas antes de uma chamada de recuperação e geração
* Citações que não possuem correspondência no contexto recuperado são sinalizadas na resposta, em vez de serem apresentadas silenciosamente como fatos

> <img width="1066" height="843" alt="image" src="https://github.com/user-attachments/assets/b65797a6-e6ee-4d03-9d75-e2ee82348830" />



## Estrutura do projeto

```text
DarkRag/
├── data/                       # _indice.json (metadados dos artigos) + PDFs baixados
├── scripts/
│   └── download_papers.py      # pesquisa e baixa artigos do arXiv
├── src/
│   ├── backend/
│   │   ├── ingest.py           # divide, gera embeddings e indexa os artigos no Qdrant
│   │   ├── query.py            # pipeline de recuperação + geração
│   │   ├── guardrails.py       # classificação de escopo + verificação de citações
│   │   ├── api.py              # aplicação FastAPI
│   │   └── Dockerfile
│   └── frontend/
│       ├── app.py              # interface de chat do Streamlit
│       └── Dockerfile
├── docker-compose.yml
├── requirements-backend.txt
├── requirements-frontend.txt
├── .env.example
└── README.md
```

## Executando o projeto

### Pré-requisitos

* Python 3.11+ (caso execute sem Docker)
* Docker e Docker Compose (recomendado)
* Um cluster do [Qdrant Cloud](https://cloud.qdrant.io) (o plano gratuito é suficiente)
* Uma chave de API do [Groq](https://console.groq.com)

### 1. Configurar as variáveis de ambiente

Copie o arquivo de exemplo e preencha suas próprias credenciais:

```bash
cp .env.example .env
```

### 2. Baixar os artigos

```bash
cd scripts
python download_papers.py
```

Isso fará o download dos PDFs para `data/`, juntamente com um arquivo de metadados `_indice.json`.

### 3. Indexar os artigos no Qdrant

A partir do diretório `src/`:

```bash
pip install -r ../requirements-backend.txt docling transformers tqdm
cd src
python backend/ingest.py
```

O `ingest.py` precisa das bibliotecas `docling` e `transformers`, que não estão incluídas propositalmente no `requirements-backend.txt`. Elas são necessárias apenas durante essa etapa de indexação, realizada uma única vez, e não são necessárias para executar a API.

### 4. Executar com Docker Compose (recomendado)

A partir da raiz do projeto:

```bash
docker compose up --build
```

* API: http://localhost:8000/docs (Swagger UI)
* Frontend: http://localhost:8501

### 4b. Ou executar localmente sem Docker

```bash
# Terminal 1 — API
pip install -r requirements-backend.txt
uvicorn src.backend.api:app --reload

# Terminal 2 — Frontend
pip install -r requirements-frontend.txt
streamlit run src/frontend/app.py
```

## Limitações conhecidas

* **Sem autenticação na API** — aceitável para um projeto local/de portfólio, mas seria necessário implementar uma chave de API ou mecanismo semelhante antes de qualquer implantação pública
* **Classificador de perguntas fora do escopo baseado em LLM** — utiliza heurísticas e pode ocasionalmente classificar incorretamente perguntas ambíguas
* **Verificação de citações baseada em correspondência de substring nos títulos** — pode produzir falsos positivos ou falsos negativos quando as citações são muito parafraseadas
* **Não está disponível publicamente** — o projeto foi desenvolvido para ser executado localmente como demonstração de todo o ciclo de desenvolvimento de uma aplicação RAG

## Licença

MIT — consulte o arquivo [LICENSE](LICENSE).
