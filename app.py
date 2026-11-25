from flask import Flask, render_template, request, jsonify
import pandas as pd
from pathlib import Path
import unicodedata

app = Flask(__name__)

# Caminho da pasta onde estão app.py, data.csv, efetivo.csv e templates/
BASE_DIR = Path(r"N:\Fiscalizacao CCO\Coordenacao da Fiscalizacao\23 NOTIFICAÇÕES AFI\Ranking_HTML")

ARQUIVO_RANKING = BASE_DIR / "data.csv"
ARQUIVO_EFETIVO = BASE_DIR / "efetivo.csv"

ranking = None
efetivo = None


def normalizar_texto(valor):
    """
    Remove acentos, espaços duplicados e padroniza em maiúsculas.
    Usado para comparar nomes e colunas.
    """
    valor = str(valor).strip()
    valor = " ".join(valor.split())
    valor = unicodedata.normalize("NFD", valor)
    valor = "".join(c for c in valor if unicodedata.category(c) != "Mn")
    return valor.upper()


def normalizar_matricula(valor):
    """
    Mantém apenas números da matrícula.
    Evita erro se vier com espaço, ponto, traço etc.
    """
    return "".join(c for c in str(valor) if c.isdigit())


def normalizar_coluna(coluna):
    """
    Normaliza nomes de colunas.
    Exemplo:
    'Mês Referência' -> 'MES_REFERENCIA'
    'AnoMes' -> 'ANOMES'
    """
    coluna = normalizar_texto(coluna)
    coluna = coluna.replace(" ", "_")
    coluna = coluna.replace("-", "_")
    coluna = coluna.replace("/", "_")
    return coluna


def formatar_mes_referencia(valor):
    """
    Converte valores como:
    2026-11 -> Novembro de 2026
    202611  -> Novembro de 2026
    11/2026 -> Novembro de 2026

    Se já vier escrito, retorna o valor original.
    """
    valor = str(valor).strip()

    if not valor:
        return ""

    meses = {
        "01": "Janeiro",
        "02": "Fevereiro",
        "03": "Março",
        "04": "Abril",
        "05": "Maio",
        "06": "Junho",
        "07": "Julho",
        "08": "Agosto",
        "09": "Setembro",
        "10": "Outubro",
        "11": "Novembro",
        "12": "Dezembro"
    }

    # Caso venha como 2026-11 ou 2026-11-01
    if "-" in valor:
        partes = valor.split("-")

        if len(partes) >= 2:
            ano = partes[0]
            mes = partes[1].zfill(2)

            if ano.isdigit() and mes in meses:
                return f"{meses[mes]} de {ano}"

    # Caso venha como 202611
    if len(valor) == 6 and valor.isdigit():
        ano = valor[:4]
        mes = valor[4:6]

        if mes in meses:
            return f"{meses[mes]} de {ano}"

    # Caso venha como 11/2026
    if "/" in valor:
        partes = valor.split("/")

        if len(partes) >= 2:
            mes = partes[0].zfill(2)
            ano = partes[1]

            if ano.isdigit() and mes in meses:
                return f"{meses[mes]} de {ano}"

    # Caso já venha como "Novembro de 2026"
    return valor


def ler_csv(caminho):
    """
    Lê CSV tentando primeiro ponto e vírgula e depois vírgula.
    Também trata UTF-8 e Latin1.
    """
    try:
        df = pd.read_csv(
            caminho,
            sep=";",
            dtype=str,
            encoding="utf-8-sig"
        ).fillna("")

        # Se veio só uma coluna, provavelmente o separador está errado
        if len(df.columns) == 1:
            df = pd.read_csv(
                caminho,
                sep=",",
                dtype=str,
                encoding="utf-8-sig"
            ).fillna("")

    except UnicodeDecodeError:
        df = pd.read_csv(
            caminho,
            sep=";",
            dtype=str,
            encoding="latin1"
        ).fillna("")

        if len(df.columns) == 1:
            df = pd.read_csv(
                caminho,
                sep=",",
                dtype=str,
                encoding="latin1"
            ).fillna("")

    df.columns = df.columns.astype(str).str.strip()

    return df


def padronizar_colunas(df):
    """
    Cria um mapa de colunas normalizadas para encontrar colunas
    mesmo com acento, sem acento, maiúsculas, minúsculas etc.
    """
    mapa = {}

    for coluna in df.columns:
        chave = normalizar_coluna(coluna)
        mapa[chave] = coluna

    return mapa


def obter_coluna(mapa_colunas, possibilidades):
    """
    Encontra a coluna real do CSV a partir de possíveis nomes.
    """
    for nome in possibilidades:
        chave = normalizar_coluna(nome)

        if chave in mapa_colunas:
            return mapa_colunas[chave]

    return None


def carregar_bases():
    global ranking, efetivo

    print("Pasta base:", BASE_DIR)
    print("Arquivo ranking:", ARQUIVO_RANKING)
    print("Arquivo efetivo:", ARQUIVO_EFETIVO)

    if not ARQUIVO_RANKING.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_RANKING}")

    if not ARQUIVO_EFETIVO.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_EFETIVO}")

    ranking = ler_csv(ARQUIVO_RANKING)
    efetivo = ler_csv(ARQUIVO_EFETIVO)

    print("Colunas ranking encontradas:", list(ranking.columns))
    print("Colunas efetivo encontradas:", list(efetivo.columns))

    mapa_ranking = padronizar_colunas(ranking)
    mapa_efetivo = padronizar_colunas(efetivo)

    col_nome_ranking = obter_coluna(mapa_ranking, [
        "Nome",
        "Nome Fiscal",
        "Fiscal",
        "Colaborador",
        "Nome do Fiscal"
    ])

    col_posicao = obter_coluna(mapa_ranking, [
        "Posição",
        "Posicao",
        "Ranking",
        "Classificação",
        "Classificacao"
    ])

    col_notificacoes = obter_coluna(mapa_ranking, [
        "Notificações",
        "Notificacoes",
        "Qtd Notificações",
        "Qtd Notificacoes",
        "Quantidade Notificações",
        "Quantidade Notificacoes"
    ])

    col_fiscalizacoes = obter_coluna(mapa_ranking, [
        "Fiscalizações",
        "Fiscalizacoes",
        "Ficalizaçoes",
        "Ficalizacoes",
        "Qtd Fiscalizações",
        "Qtd Fiscalizacoes",
        "Quantidade Fiscalizações",
        "Quantidade Fiscalizacoes"
    ])

    col_mes = obter_coluna(mapa_ranking, [
        "Mês Referência",
        "Mes Referencia",
        "Mês de Referência",
        "Mes de Referencia",
        "Mês",
        "Mes",
        "Referência",
        "Referencia",
        "AnoMes",
        "Ano Mes",
        "Ano-Mes",
        "Ano/Mes",
        "Ano Mês"
    ])

    col_nome_efetivo = obter_coluna(mapa_efetivo, [
        "Nome",
        "Nome Fiscal",
        "Fiscal",
        "Colaborador",
        "Nome do Fiscal"
    ])

    col_matricula = obter_coluna(mapa_efetivo, [
        "Matrícula GM",
        "Matricula GM",
        "Matrícula",
        "Matricula",
        "GM"
    ])

    if not col_nome_ranking:
        raise Exception(
            "Não encontrei a coluna de nome no arquivo data.csv. "
            f"Colunas encontradas: {list(ranking.columns)}"
        )

    if not col_posicao:
        raise Exception(
            "Não encontrei a coluna de posição no arquivo data.csv. "
            f"Colunas encontradas: {list(ranking.columns)}"
        )

    if not col_notificacoes:
        print("Atenção: coluna de notificações não encontrada no data.csv.")

    if not col_fiscalizacoes:
        print("Atenção: coluna de fiscalizações não encontrada no data.csv.")

    if not col_mes:
        print("Atenção: coluna de mês referência não encontrada no data.csv.")

    if not col_nome_efetivo:
        raise Exception(
            "Não encontrei a coluna de nome no arquivo efetivo.csv. "
            f"Colunas encontradas: {list(efetivo.columns)}"
        )

    if not col_matricula:
        raise Exception(
            "Não encontrei a coluna Matrícula GM no arquivo efetivo.csv. "
            f"Colunas encontradas: {list(efetivo.columns)}"
        )

    # Renomeia colunas principais do ranking para um padrão interno
    renomear_ranking = {
        col_nome_ranking: "Nome",
        col_posicao: "Posição"
    }

    if col_notificacoes:
        renomear_ranking[col_notificacoes] = "Notificações"

    if col_fiscalizacoes:
        renomear_ranking[col_fiscalizacoes] = "Fiscalizações"

    if col_mes:
        renomear_ranking[col_mes] = "Mês Referência"

    ranking.rename(columns=renomear_ranking, inplace=True)

    # Renomeia colunas principais do efetivo para um padrão interno
    efetivo.rename(columns={
        col_nome_efetivo: "Nome",
        col_matricula: "Matrícula GM"
    }, inplace=True)

    # Limpa campos principais
    ranking["Nome"] = ranking["Nome"].astype(str).str.strip()
    efetivo["Nome"] = efetivo["Nome"].astype(str).str.strip()
    efetivo["Matrícula GM"] = efetivo["Matrícula GM"].astype(str).apply(normalizar_matricula)

    print("Bases carregadas com sucesso.")
    print(f"Ranking: {len(ranking)} registros")
    print(f"Efetivo: {len(efetivo)} registros")
    print("Colunas ranking padronizadas:", list(ranking.columns))
    print("Colunas efetivo padronizadas:", list(efetivo.columns))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/consultar")
def consultar():
    try:
        matricula = request.args.get("matricula", "")
        matricula = normalizar_matricula(matricula)

        if not matricula:
            return jsonify({
                "erro": "Matrícula não informada"
            })

        fiscal = efetivo[
            efetivo["Matrícula GM"].astype(str).apply(normalizar_matricula) == matricula
        ]

        if fiscal.empty:
            return jsonify({
                "erro": "Matrícula não encontrada"
            })

        nome = str(fiscal.iloc[0]["Nome"]).strip()

        resultado = ranking[
            ranking["Nome"].astype(str).apply(normalizar_texto) == normalizar_texto(nome)
        ]

        if resultado.empty:
            return jsonify({
                "erro": "Fiscal sem ranking no período"
            })

        linha = resultado.iloc[0]

        return jsonify({
            "nome": nome,
            "posicao": str(linha.get("Posição", "")),
            "notificacoes": str(linha.get("Notificações", "")),
            "fiscalizacoes": str(linha.get("Fiscalizações", "")),
            "mes": formatar_mes_referencia(linha.get("Mês Referência", "")),
            "matricula": matricula
        })

    except Exception as erro:
        return jsonify({
            "erro": str(erro)
        })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8054,
        debug=True
    )
