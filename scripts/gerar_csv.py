import csv
import json
import sys
from pathlib import Path


COLUNAS = [
    "ID",
    "Código",
    "Nome",
    "Categoria",
    "Preço",
    "Unidade",
    "Estoque",
    "Em promoção",
    "Preço promocional",
]


def carregar_json(caminho_json: Path) -> dict:
    try:
        with caminho_json.open(
            "r",
            encoding="utf-8"
        ) as arquivo:
            dados = json.load(arquivo)

    except FileNotFoundError:
        raise RuntimeError(
            f"Arquivo não encontrado: {caminho_json}"
        )

    except json.JSONDecodeError as erro:
        raise RuntimeError(
            f"JSON inválido: {erro}"
        )

    if not isinstance(dados, dict):
        raise RuntimeError(
            "O JSON deve conter um objeto principal."
        )

    if "products" not in dados:
        raise RuntimeError(
            "O JSON não possui a chave 'products'."
        )

    if not isinstance(dados["products"], list):
        raise RuntimeError(
            "'products' não é uma lista válida."
        )

    return dados


def gerar_csv(dados: dict, caminho_csv: Path) -> int:
    produtos = dados["products"]

    try:
        with caminho_csv.open(
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as arquivo_csv:

            writer = csv.DictWriter(
                arquivo_csv,
                fieldnames=COLUNAS
            )

            writer.writeheader()

            for produto in produtos:
                if not isinstance(produto, dict):
                    continue

                writer.writerow({
                    "ID": produto.get("id", ""),
                    "Código": produto.get("codigo", ""),
                    "Nome": produto.get("nome", ""),
                    "Categoria": produto.get("categoria", ""),
                    "Preço": produto.get("valor", ""),
                    "Unidade": produto.get("unidade", ""),
                    "Estoque": produto.get("estoque", ""),
                    "Em promoção": produto.get(
                        "em_promocao",
                        False
                    ),
                    "Preço promocional": produto.get(
                        "preco_promocional",
                        ""
                    ),
                })

    except OSError as erro:
        raise RuntimeError(
            f"Erro ao criar o CSV: {erro}"
        )

    return len(produtos)


def main():
    if len(sys.argv) != 3:
        print(
            "Uso: python scripts/gerar_csv.py "
            "<produtos.json> <estoque.csv>",
            file=sys.stderr
        )
        sys.exit(1)

    caminho_json = Path(sys.argv[1])
    caminho_csv = Path(sys.argv[2])

    try:
        dados = carregar_json(caminho_json)

        quantidade = gerar_csv(
            dados,
            caminho_csv
        )

        print(f"CSV criado: {caminho_csv}")
        print(f"Produtos processados: {quantidade}")

    except RuntimeError as erro:
        print(
            f"ERRO: {erro}",
            file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()