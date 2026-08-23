import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'resources'))
from catalogo_api import CatalogoAPI

HISTORICO_DIR = "historico"
ULTIMO_SNAPSHOT = os.path.join(HISTORICO_DIR, "ultimo_snapshot.json")
ARQUIVO_VENDAS_ACUMULADAS = "vendas_acumuladas.csv"

def carregar_ultimo_snapshot():
    if os.path.exists(ULTIMO_SNAPSHOT):
        with open(ULTIMO_SNAPSHOT, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def salvar_snapshot(produtos_com_estoque):
    os.makedirs(HISTORICO_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo = os.path.join(HISTORICO_DIR, f"snapshot_{timestamp}.json")
    dados = {
        "timestamp": timestamp,
        "produtos": {
            str(p['id']): {
                "estoque": p.get('estoque', 0),
                "valor": p.get('valor', 0)
            } for p in produtos_com_estoque
        }
    }
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    with open(ULTIMO_SNAPSHOT, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return arquivo

def extrair_estoque_anterior(valor):
    if isinstance(valor, dict):
        return int(valor.get('estoque', 0))
    else:
        return int(valor)

def extrair_valor_anterior(valor):
    if isinstance(valor, dict):
        return float(valor.get('valor', 0))
    else:
        return 0.0

def gerar_relatorio_vendas(snapshot_anterior, produtos_atuais):
    vendas = []
    reposicoes = []
    sem_mudanca = 0

    dict_atual = {
        str(p['id']): {
            "estoque": p.get('estoque', 0),
            "valor": p.get('valor', 0)
        } for p in produtos_atuais
    }
    dict_anterior = snapshot_anterior.get('produtos', {})

    todos_ids = set(dict_anterior.keys()) | set(dict_atual.keys())

    for pid in todos_ids:
        qtd_anterior = extrair_estoque_anterior(dict_anterior.get(pid, {"estoque": 0}))
        qtd_atual = int(dict_atual.get(pid, {"estoque": 0})["estoque"])
        valor_unit = float(dict_atual.get(pid, {"valor": 0})["valor"])
        diferenca = qtd_atual - qtd_anterior

        nome = next((p.get('nome', p.get('descricao', '')) for p in produtos_atuais if str(p['id']) == pid), '')

        if diferenca < 0:
            vendas.append({
                'id': pid,
                'nome': nome,
                'qtd_anterior': qtd_anterior,
                'qtd_atual': qtd_atual,
                'unidades': abs(diferenca),
                'valor_unit': valor_unit,
                'valor_total': abs(diferenca) * valor_unit
            })
        elif diferenca > 0:
            reposicoes.append({
                'id': pid,
                'nome': nome,
                'qtd_anterior': qtd_anterior,
                'qtd_atual': qtd_atual,
                'unidades': diferenca,
                'valor_unit': valor_unit,
                'valor_total': diferenca * valor_unit
            })
        else:
            sem_mudanca += 1

    return vendas, reposicoes, sem_mudanca

def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):.2f}"
    except:
        return "R$ 0.00"

def main():
    print("=" * 80)
    print("🚀 MONITORAMENTO DE CATÁLOGO E VENDAS")
    print("=" * 80)

    api = CatalogoAPI()

    print("\n🔍 Buscando catálogo...")
    catalogo = api.buscar_catalogo_completo()
    if not catalogo.get('success', True):
        print(f"❌ Erro ao buscar catálogo: {catalogo.get('error', 'Desconhecido')}")
        return

    produtos = api.extrair_produtos(catalogo)
    print(f"✅ {len(produtos)} produtos encontrados")

    com_estoque = [p for p in produtos if p.get('estoque') is not None and int(p['estoque']) > 0]
    print(f"📦 Produtos com estoque > 0: {len(com_estoque)}")

    snap_anterior = carregar_ultimo_snapshot()
    arquivo_snapshot = salvar_snapshot(com_estoque)
    print(f"💾 Snapshot salvo em: {arquivo_snapshot}")

    if snap_anterior:
        vendas, reposicoes, sem_mudanca = gerar_relatorio_vendas(snap_anterior, com_estoque)
        print("\n" + "=" * 80)
        print("📈 RELATÓRIO DE VENDAS (desde a última execução)")
        print("=" * 80)
        print(f"Produtos sem mudança: {sem_mudanca}")
        print(f"Produtos vendidos: {len(vendas)}")
        print(f"Produtos repostos: {len(reposicoes)}")

        if vendas:
            print("\n--- VENDAS ---")
            for v in vendas:
                print(f"{v['unidades']:>4} un. | {v['nome']} (ID {v['id']}) | anterior: {v['qtd_anterior']}, atual: {v['qtd_atual']} | valor: {formatar_moeda(v['valor_total'])}")

            # Apendar vendas ao arquivo acumulativo
            timestamp_agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            arquivo_existe = os.path.exists(ARQUIVO_VENDAS_ACUMULADAS)

            with open(ARQUIVO_VENDAS_ACUMULADAS, 'a', encoding='utf-8') as f:
                if not arquivo_existe:
                    f.write("DATA_HORA;ID;NOME;QUANTIDADE_VENDIDA;VALOR_TOTAL\n")
                for v in vendas:
                    f.write(f"{timestamp_agora};{v['id']};{v['nome']};{v['unidades']};{v['valor_total']}\n")
            print(f"📁 Vendas acumuladas salvas em: {ARQUIVO_VENDAS_ACUMULADAS}")

        if reposicoes:
            print("\n--- REPOSIÇÕES ---")
            for r in reposicoes:
                print(f"+{r['unidades']:>4} un. | {r['nome']} (ID {r['id']}) | anterior: {r['qtd_anterior']}, atual: {r['qtd_atual']} | valor: {formatar_moeda(r['valor_total'])}")

        # Resumo de movimentações
        total_vendido = sum(v['unidades'] for v in vendas)
        total_comprado = sum(r['unidades'] for r in reposicoes)
        valor_vendido = sum(v['valor_total'] for v in vendas)
        valor_comprado = sum(r['valor_total'] for r in reposicoes)

        print("\n" + "=" * 80)
        print("📊 RESUMO DE MOVIMENTAÇÕES")
        print("=" * 80)
        print(f"Unidades vendidas: {total_vendido}")
        print(f"Valor total vendido: {formatar_moeda(valor_vendido)}")
        print(f"Unidades repostas (compradas): {total_comprado}")
        print(f"Valor total reposto: {formatar_moeda(valor_comprado)}")

        with open('movimentacoes.csv', 'w', encoding='utf-8') as f:
            f.write("TIPO;ID;NOME;UNIDADES;VALOR_UNITARIO;VALOR_TOTAL;QTD_ANTERIOR;QTD_ATUAL\n")
            for v in vendas:
                f.write(f"VENDA;{v['id']};{v['nome']};{v['unidades']};{v['valor_unit']};{v['valor_total']};{v['qtd_anterior']};{v['qtd_atual']}\n")
            for r in reposicoes:
                f.write(f"REPOSICAO;{r['id']};{r['nome']};{r['unidades']};{r['valor_unit']};{r['valor_total']};{r['qtd_anterior']};{r['qtd_atual']}\n")
        print("📁 CSV de movimentações salvo: movimentacoes.csv")
    else:
        print("\n📌 Primeira execução: nenhum snapshot anterior para comparar.")

    # Agrupar por categoria para exibição
    categorias = {}
    for p in com_estoque:
        cat = p.get('categoria', 'OUTROS')
        categorias.setdefault(cat, []).append(p)

    print("\n" + "=" * 80)
    print("📋 CATÁLOGO ORGANIZADO POR CATEGORIA")
    print("=" * 80)

    total_geral = 0
    valor_geral = 0.0

    for categoria in sorted(categorias.keys()):
        produtos_cat = sorted(categorias[categoria], key=lambda x: x.get('nome', '').lower())
        qtd_cat = len(produtos_cat)
        valor_cat = sum(float(p.get('valor', 0)) for p in produtos_cat)
        total_geral += qtd_cat
        valor_geral += valor_cat

        print(f"\n📂 {categoria}  ({qtd_cat} produtos)")
        print("-" * 80)
        print(f"{'ID':<6} {'Nome':<40} {'Qtd':>5} {'Valor':>10}")
        print("-" * 80)

        for p in produtos_cat:
            id_str = str(p.get('id', ''))
            nome = p.get('nome', p.get('descricao', ''))
            qtd = int(p.get('estoque', 0))
            valor = float(p.get('valor', 0))
            nome_exib = nome[:38] + '..' if len(nome) > 40 else nome
            print(f"{id_str:<6} {nome_exib:<40} {qtd:>5} {formatar_moeda(valor):>10}")

        print(f"{'':<6} {'Total da categoria':<40} {qtd_cat:>5} {formatar_moeda(valor_cat):>10}")

    print("\n" + "=" * 80)
    print(f"TOTAL GERAL: {total_geral} produtos | Valor total: {formatar_moeda(valor_geral)}")
    print("=" * 80)

    with open('catalogo_por_categoria.csv', 'w', encoding='utf-8') as f:
        f.write("CATEGORIA;ID;NOME;QUANTIDADE;VALOR\n")
        for categoria in sorted(categorias.keys()):
            for p in sorted(categorias[categoria], key=lambda x: x.get('nome', '').lower()):
                f.write(f"{categoria};{p['id']};{p.get('nome','')};{p.get('estoque', 0)};{p.get('valor', 0)}\n")
    print("\n📁 CSV por categoria salvo: catalogo_por_categoria.csv")

    with open('catalogo_geral.csv', 'w', encoding='utf-8') as f:
        f.write("ID;NOME;QUANTIDADE;VALOR;CATEGORIA\n")
        for p in sorted(com_estoque, key=lambda x: int(x.get('id', 0))):
            f.write(f"{p['id']};{p.get('nome','')};{p.get('estoque', 0)};{p.get('valor', 0)};{p.get('categoria','')}\n")
    print("📁 CSV geral salvo: catalogo_geral.csv")

    print("\n✅ Execução concluída!")

if __name__ == "__main__":
    main()