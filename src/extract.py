import os
from pypdf import PdfReader
import json

PASTA_PDFS = "../data/raw"
PASTA_SAIDA = "../data/processed"
os.makedirs(PASTA_SAIDA, exist_ok=True)


def extrair_texto_pdf(caminho_pdf):
    reader = PdfReader(caminho_pdf)
    return "\n\n".join(p.extract_text() or "" for p in reader.pages)


def limpar_texto(texto):
    texto = texto.replace("-\n", "")
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    return "\n".join(linhas)


def main():
    pdfs = [f for f in os.listdir(PASTA_PDFS) if f.endswith(".pdf")]
    if not pdfs:
        print(f"Nenhum PDF encontrado em {PASTA_PDFS}")
        return

    relatorio = []
    for nome in pdfs:
        try:
            texto = limpar_texto(extrair_texto_pdf(os.path.join(PASTA_PDFS, nome)))
            with open(
                os.path.join(PASTA_SAIDA, nome.replace(".pdf", ".txt")),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(texto)
            n = len(texto)
            status = "OK" if n > 500 else "SUSPEITO (pouco texto extraído)"
            print(f"{nome}: {status} ({n} caracteres)")
            relatorio.append(
                {"arquivo": nome, "caracteres_extraidos": n, "status": status}
            )
        except Exception as e:
            print(f"{nome}: ERRO {e}")
            relatorio.append(
                {"arquivo": nome, "caracteres_extraidos": 0, "status": f"ERRO: {e}"}
            )

    with open(
        os.path.join(PASTA_SAIDA, "_relatorio_extracao.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)
    suspeitos = [
        r for r in relatorio if "SUSPEITO" in r["status"] or "ERRO" in r["status"]
    ]
    print(
        f"\n{len(relatorio) - len(suspeitos)}/{len(relatorio)} extraídos com sucesso."
    )
    if suspeitos:
        print(
            f"⚠ {len(suspeitos)} arquivo(s) com problema — veja _relatorio_extracao.json"
        )


if __name__ == "__main__":
    main()
