# %%

import os
import re
import json
import unicodedata
from pypdf import PdfReader

PASTA_PDFS = "../data/raw"
PASTA_SAIDA = "../data/processed"
os.makedirs(PASTA_SAIDA, exist_ok=True)


def extrair_texto_pdf(caminho_pdf):
    reader = PdfReader(caminho_pdf)
    texto_paginas = []
    for pagina in reader.pages:
        texto = pagina.extract_text() or ""
        texto_paginas.append(texto)
    return "\n\n".join(texto_paginas)


def limpar_texto(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.replace("-\n", "")
    texto = re.sub(r"\s+([,.;:)])", r"\1", texto)
    texto = re.sub(r"([(])\s+", r"\1", texto)
    linhas = [linha.strip() for linha in texto.split("\n")]
    linhas = [linha for linha in linhas if linha]
    return "\n".join(linhas)


def main():
    arquivos_pdf = [f for f in os.listdir(PASTA_PDFS) if f.endswith(".pdf")]
    if not arquivos_pdf:
        print(f"Nenhum PDF encontrado em {PASTA_PDFS}")
        return
    relatorio = []
    for nome_arquivo in arquivos_pdf:
        caminho_pdf = os.path.join(PASTA_PDFS, nome_arquivo)
        print(f"Extraindo: {nome_arquivo}")
        try:
            texto_bruto = extrair_texto_pdf(caminho_pdf)
            texto_limpo = limpar_texto(texto_bruto)
            nome_saida = nome_arquivo.replace(".pdf", ".txt")
            caminho_saida = os.path.join(PASTA_SAIDA, nome_saida)
            with open(caminho_saida, "w", encoding="utf-8") as f:
                f.write(texto_limpo)
            num_caracteres = len(texto_limpo)
            status = "OK" if num_caracteres > 500 else "SUSPEITO (pouco texto extraído)"
            print(f"  {status} — {num_caracteres} caracteres")
            relatorio.append(
                {
                    "arquivo": nome_arquivo,
                    "caracteres_extraidos": num_caracteres,
                    "status": status,
                }
            )
        except Exception as e:
            print(f"  [ERRO] Falha ao processar {nome_arquivo}: {e}")
            relatorio.append(
                {
                    "arquivo": nome_arquivo,
                    "caracteres_extraidos": 0,
                    "status": f"ERRO: {e}",
                }
            )
    with open(
        os.path.join(PASTA_SAIDA, "_relatorio_extracao.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)
    suspeitos = [
        r for r in relatorio if "SUSPEITO" in r["status"] or "ERRO" in r["status"]
    ]
    print(
        f"\nConcluído. {len(relatorio) - len(suspeitos)}/{len(relatorio)} extraídos com sucesso."
    )
    if suspeitos:
        print(
            f"⚠ {len(suspeitos)} arquivo(s) com problema — veja _relatorio_extracao.json"
        )


if __name__ == "__main__":
    main()
