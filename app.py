from flask import Flask, render_template, request, jsonify
import pandas as pd
from pathlib import Path
import unicodedata
import os
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


app = Flask(__name__)

# ============================================================
# CONFIGURAÇÃO PARA RENDER
# ============================================================
# Estrutura esperada:
#
# projeto/
# ├── app.py
# ├── data.csv
# ├── efetivo.csv
# ├── requirements.txt
# └── templates/
#     └── index.html
#
# No Render, não use caminho N:\.
# Os arquivos CSV precisam estar junto do projeto ou em DATA_DIR.

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR)).resolve()

ARQUIVO_RANKING = DATA_DIR / "data.csv"
ARQUIVO_EFETIVO = DATA_DIR / "efetivo.csv"

ranking = None
efetivo = None


# ============================================================
# FUNÇÕES DE NORMALIZAÇÃO
# ============================================================

def normalizar_texto(valor):
    valor = str(valor).strip()
    valor = " ".join(valor.split())
    valor = unicodedata.normalize("NFD", valor)
    valor = "".join(c for c in valor if unicodedata.category(c) != "Mn")
    return valor.upper()


def normalizar_matricula(valor):
    return "".join(c for c in str(valor) if c.isdigit())


def normalizar_coluna(coluna):
    coluna = normalizar_texto(coluna)
    coluna = coluna.replace(" ", "_")
    coluna = coluna.replace("-", "_")
    coluna = coluna.replace("/", "_")
    coluna = coluna.replace(".", "_")
    return coluna


def formatar_mes_referencia(valor):
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

    # Formato: 2026-11 ou 2026-11-01
    if "-" in valor:
        partes = valor.split("-")

        if len(partes) >= 2:
            ano = partes[0]
            mes = partes[1].zfill(2)

            if ano.isdigit() and mes in meses:
                return f"{meses[mes]} de {ano}"

    # Formato: 202611
    if len(valor) == 6 and valor.isdigit():
        ano = valor[:4]
        mes = valor[4:6]

        if mes in meses:
            return f"{meses[mes]} de {ano}"

    # Formato: 11/2026
    if "/" in valor:
        partes = valor.split("/")

        if len(partes) >= 2:
            mes = partes[0].zfill(2)
            ano = partes[1]

            if ano.isdigit() and mes in meses:
                return f"{meses[mes]} de {ano}"

    return valor


def obter_ultima_atualizacao_base():
    """
    Retorna a data/hora da última modificação do data.csv.
    Essa data será exibida no HTML como a última atualização da base.
    """
    try:
        if not ARQUIVO_RANKING.exists():
            return ""

        timestamp = ARQUIVO_RANKING.stat().st_mtime

        if ZoneInfo:
            data_hora = datetime.fromtimestamp(timestamp, ZoneInfo("America/Sao_Paulo"))
        else:
            data_hora = datetime.fromtimestamp(timestamp)

        return data_hora.strftime("%d/%m/%Y às %H:%M")

    except Exception:
        return ""


# ============================================================
# LEITURA DOS CSVs
# ============================================================

def ler_csv(caminho):
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    tentativas = [
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "latin1"},
        {"sep": ",", "encoding": "latin1"},
    ]

    ultimo_erro = None

    for tentativa in tentativas:
        try:
            df = pd.read_csv(
                caminho,
                sep=tentativa["sep"],
                dtype=str,
                encoding=tentativa["encoding"]
            ).fillna("")

            if len(df.columns) > 1:
                df.columns = df.columns.astype(str).str.strip()
                return df

            ultimo_erro = f"CSV lido com apenas uma coluna usando {tentativa}"

        except Exception as erro:
            ultimo_erro = erro

    raise Exception(f"Não foi possível ler o arquivo {caminho}. Erro: {ultimo_erro}")


def padronizar_colunas(df):
    mapa = {}

    for coluna in df.columns:
        chave = normalizar_coluna(coluna)
        mapa[chave] = coluna

    return mapa


def obter_coluna(mapa_colunas, possibilidades):
    for nome in possibilidades:
        chave = normalizar_coluna(nome)

        if chave in mapa_colunas:
            return mapa_colunas[chave]

    return None


# ============================================================
# CARREGAMENTO DAS BASES
# ============================================================

def carregar_bases():
    global ranking, efetivo

    print("==============================================")
    print("Carregando bases...")
    print("BASE_DIR:", BASE_DIR)
    print("DATA_DIR:", DATA_DIR)
    print("Arquivo ranking:", ARQUIVO_RANKING)
    print("Arquivo efetivo:", ARQUIVO_EFETIVO)
    print("Última atualização data.csv:", obter_ultima_atualizacao_base())
    print("==============================================")

    if not ARQUIVO_RANKING.exists():
        raise FileNotFoundError(
            f"Arquivo data.csv não encontrado em: {ARQUIVO_RANKING}"
        )

    if not ARQUIVO_EFETIVO.exists():
        raise FileNotFoundError(
            f"Arquivo efetivo.csv não encontrado em: {ARQUIVO_EFETIVO}"
        )

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

    if not col_notificacoes:
        print("Atenção: coluna de notificações não encontrada no data.csv.")

    if not col_fiscalizacoes:
        print("Atenção: coluna de fiscalizações não encontrada no data.csv.")

    if not col_mes:
        print("Atenção: coluna de mês referência não encontrada no data.csv.")

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

    efetivo.rename(columns={
        col_nome_efetivo: "Nome",
        col_matricula: "Matrícula GM"
    }, inplace=True)

    ranking["Nome"] = ranking["Nome"].astype(str).str.strip()
    efetivo["Nome"] = efetivo["Nome"].astype(str).str.strip()
    efetivo["Matrícula GM"] = efetivo["Matrícula GM"].astype(str).apply(normalizar_matricula)

    print("Bases carregadas com sucesso.")
    print(f"Ranking: {len(ranking)} registros")
    print(f"Efetivo: {len(efetivo)} registros")
    print("Colunas ranking padronizadas:", list(ranking.columns))
    print("Colunas efetivo padronizadas:", list(efetivo.columns))
    print("Última atualização da base:", obter_ultima_atualizacao_base())
    print("==============================================")


def garantir_bases_carregadas():
    global ranking, efetivo

    if ranking is None or efetivo is None:
        print("Bases ainda não carregadas. Carregando agora...")
        carregar_bases()


# ============================================================
# ROTAS
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "ranking_existe": ARQUIVO_RANKING.exists(),
        "efetivo_existe": ARQUIVO_EFETIVO.exists(),
        "ultima_atualizacao_base": obter_ultima_atualizacao_base()
    })


@app.route("/recarregar-bases")
def recarregar_bases():
    """
    Recarrega os CSVs sem reiniciar o serviço.
    Atenção: em produção, o ideal é proteger esta rota com senha/login.
    """
    try:
        carregar_bases()

        return jsonify({
            "status": "ok",
            "mensagem": "Bases recarregadas com sucesso.",
            "ranking": len(ranking),
            "efetivo": len(efetivo),
            "ultima_atualizacao_base": obter_ultima_atualizacao_base()
        })

    except Exception as erro:
        return jsonify({
            "status": "erro",
            "erro": str(erro)
        }), 500


@app.route("/consultar")
def consultar():
    try:
        garantir_bases_carregadas()

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
            "matricula": matricula,
            "atualizacao_base": obter_ultima_atualizacao_base()
        })

    except Exception as erro:
        print("Erro na consulta:", erro)

        return jsonify({
            "erro": str(erro)
        }), 500


# ============================================================
# EXECUÇÃO LOCAL
# ============================================================
# No Render, use:
# gunicorn app:app
#
# Localmente, use:
# python app.py

if __name__ == "__main__":
    carregar_bases()

    porta = int(os.environ.get("PORT", 8054))

    app.run(
        host="0.0.0.0",
        port=porta,
        debug=True,
        use_reloader=False
    )
