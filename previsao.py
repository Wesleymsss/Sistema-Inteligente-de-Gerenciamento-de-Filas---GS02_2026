"""Regressão linear com histórico de filas explicitamente simulado."""

import csv
import json
import random
from pathlib import Path
from statistics import mean

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

BASE = Path(__file__).resolve().parent
COLUNAS = ["sessao", "pessoas_aguardando", "media_recente_min", "residual_estimado_min", "espera_observada_min", "origem"]


def gerar_historico(destino):
    """Simula um balcão FIFO. Somente serviços já concluídos formam a média."""
    rng = random.Random(2026)
    registros = []
    for sessao in range(50):
        ritmo = rng.uniform(3.0, 7.0)
        chegada = 0.0
        servicos = []
        for _ in range(50):
            chegada += rng.expovariate(1 / 6.0)
            concluidos = [fim - inicio for inicio, fim in servicos if fim <= chegada]
            media_recente = mean(concluidos[-5:]) if concluidos else 5.0
            aguardando = sum(inicio > chegada for inicio, fim in servicos)
            ativo = next(((inicio, fim) for inicio, fim in servicos if inicio <= chegada < fim), None)
            residual = max(0.0, media_recente - (chegada - ativo[0])) if ativo else 0.0
            inicio = max(chegada, servicos[-1][1] if servicos else chegada)
            duracao = max(0.5, rng.gauss(ritmo, 1.3))
            servicos.append((inicio, inicio + duracao))
            registros.append([sessao, aguardando, round(media_recente, 6), round(residual, 6), round(inicio - chegada, 6), "simulado"])
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(COLUNAS)
        escritor.writerows(registros)


def atributos(pessoas, media, residual):
    return [pessoas, pessoas * media, residual]


class Previsor:
    def __init__(self, caminho=None):
        caminho = Path(caminho or BASE / "dados" / "historico_simulado.csv")
        if not caminho.exists():
            gerar_historico(caminho)
        with caminho.open(encoding="utf-8") as arquivo:
            registros = list(csv.DictReader(arquivo))
        treino = [linha for linha in registros if int(linha["sessao"]) < 40]
        teste = [linha for linha in registros if int(linha["sessao"]) >= 40]

        def extrair(linhas):
            return [atributos(int(l["pessoas_aguardando"]), float(l["media_recente_min"]), float(l["residual_estimado_min"])) for l in linhas]

        self.modelo = LinearRegression().fit(extrair(treino), [float(l["espera_observada_min"]) for l in treino])
        verdade = [float(l["espera_observada_min"]) for l in teste]
        convencional = [x[1] + x[2] for x in extrair(teste)]
        prevista = [self.estimar(int(l["pessoas_aguardando"]), float(l["media_recente_min"]), float(l["residual_estimado_min"])) for l in teste]
        self.metricas = {
            "origem": "Dados simulados com semente 2026",
            "amostras_treino": len(treino), "amostras_teste": len(teste),
            "sessoes_treino": "0 a 39", "sessoes_teste": "40 a 49",
            "mae_media_min": round(mean_absolute_error(verdade, convencional), 4),
            "mae_ia_min": round(mean_absolute_error(verdade, prevista), 4),
            "intercepto": float(self.modelo.intercept_),
            "coeficientes": self.modelo.coef_.tolist(),
            "atributos": ["pessoas_aguardando", "pessoas_x_media_recente", "residual_estimado_min"],
            "maior_fila_treino": max(int(l["pessoas_aguardando"]) for l in treino),
        }

    def estimar(self, pessoas, media, residual):
        if pessoas == 0 and residual == 0:
            return 0.0
        return max(0.0, float(self.modelo.predict([atributos(pessoas, media, residual)])[0]))


if __name__ == "__main__":
    previsor = Previsor()
    destino = BASE / "dados" / "avaliacao_modelo.json"
    destino.write_text(json.dumps(previsor.metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(destino.read_text(encoding="utf-8"))
