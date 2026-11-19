"""Citizen Assist AI. Balcão único, fila FIFO e persistência transacional."""

import argparse
import csv
import io
import json
import os
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from flask import Flask, Response, jsonify, render_template, request
from waitress import serve

from previsao import Previsor

BASE = Path(__file__).resolve().parent


def horario(instante):
    return datetime.fromtimestamp(instante, timezone.utc).isoformat()


def conectar(caminho):
    banco = sqlite3.connect(caminho, timeout=10)
    banco.row_factory = sqlite3.Row
    banco.execute("PRAGMA foreign_keys=ON")
    return banco


def criar_app(caminho_banco=None, relogio=time.time):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4096
    caminho = Path(caminho_banco or os.getenv("FILA_DB", BASE / "dados" / "fila.sqlite3"))
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with closing(conectar(caminho)) as banco:
        banco.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS senhas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chegada REAL NOT NULL,
                inicio REAL,
                conclusao REAL,
                CHECK (inicio IS NULL OR inicio >= chegada),
                CHECK (conclusao IS NULL OR (inicio IS NOT NULL AND conclusao >= inicio))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS um_balcao
            ON senhas ((1)) WHERE inicio IS NOT NULL AND conclusao IS NULL;
            CREATE INDEX IF NOT EXISTS fila_aberta ON senhas (conclusao, inicio, id);
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instante REAL NOT NULL,
                acao TEXT NOT NULL,
                senha_id INTEGER REFERENCES senhas(id),
                resultado TEXT NOT NULL,
                detalhe TEXT NOT NULL,
                requisicao TEXT UNIQUE NOT NULL,
                corpo TEXT NOT NULL,
                http_status INTEGER NOT NULL
            );
        """)
    previsor = Previsor()

    def estado(banco, agora):
        pessoas = banco.execute("SELECT COUNT(*) FROM senhas WHERE inicio IS NULL").fetchone()[0]
        concluidos = banco.execute("SELECT COUNT(*) FROM senhas WHERE conclusao IS NOT NULL").fetchone()[0]
        ativo = banco.execute("SELECT * FROM senhas WHERE inicio IS NOT NULL AND conclusao IS NULL").fetchone()
        duracoes = [l[0] for l in banco.execute("SELECT (conclusao-inicio)/60.0 FROM senhas WHERE conclusao IS NOT NULL ORDER BY conclusao DESC, id DESC LIMIT 5")]
        media = mean(duracoes) if duracoes else 5.0
        decorrido = max(0.0, (agora - ativo["inicio"]) / 60) if ativo else 0.0
        residual = max(0.0, media - decorrido) if ativo else 0.0
        historico = []
        for linha in banco.execute("SELECT * FROM eventos ORDER BY id DESC LIMIT 12"):
            historico.append({"id": linha["id"], "horario": horario(linha["instante"]), "acao": linha["acao"], "senha": f'A{linha["senha_id"]:03d}' if linha["senha_id"] else "—", "resultado": linha["resultado"], "detalhe": linha["detalhe"]})
        proximas = [dict(l) for l in banco.execute("SELECT id, chegada FROM senhas WHERE inicio IS NULL ORDER BY id LIMIT 10")]
        return {"aguardando": pessoas, "concluidos": concluidos,
                "em_atendimento": {"id": ativo["id"], "senha": f'A{ativo["id"]:03d}', "inicio": horario(ativo["inicio"])} if ativo else None,
                "proximas": [{"id": l["id"], "senha": f'A{l["id"]:03d}', "chegada": horario(l["chegada"])} for l in proximas],
                "espera_media_min": round(pessoas * media + residual, 2),
                "espera_ia_min": round(previsor.estimar(pessoas, media, residual), 2),
                "media_atendimento_min": round(media, 3),
                "origem_media": "Últimos 5 atendimentos locais" if duracoes else "Referência inicial simulada de 5 min",
                "fora_faixa_treino": pessoas > previsor.metricas["maior_fila_treino"],
                "eventos": historico, "atualizado_em": horario(agora)}

    @app.after_request
    def sem_cache(resposta):
        if request.path.startswith("/api/"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.get("/")
    def painel():
        return render_template("index.html")

    @app.get("/api/estado")
    def consultar():
        with closing(conectar(caminho)) as banco:
            banco.execute("BEGIN")
            return jsonify(estado(banco, relogio()))

    @app.get("/api/modelo")
    def modelo():
        return jsonify(previsor.metricas)

    @app.get("/api/eventos.csv")
    def exportar():
        saida = io.StringIO(newline="")
        escritor = csv.writer(saida)
        escritor.writerow(["evento", "horario_utc", "acao", "senha", "resultado", "detalhe"])
        with closing(conectar(caminho)) as banco:
            for l in banco.execute("SELECT * FROM eventos ORDER BY id"):
                escritor.writerow([l["id"], horario(l["instante"]), l["acao"], l["senha_id"], l["resultado"], l["detalhe"]])
        return Response("\ufeff" + saida.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=eventos_fila.csv"})

    @app.post("/api/acao")
    def executar():
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            return jsonify(mensagem="Envie um objeto JSON."), 400
        acao = dados.get("acao")
        requisicao = dados.get("requisicao")
        if acao not in ("chegada", "iniciar", "concluir") or not isinstance(requisicao, str) or not 8 <= len(requisicao) <= 100:
            return jsonify(mensagem="Ação ou identificador de requisição inválido."), 400
        esperado = dados.get("senha_id")
        if acao != "chegada" and esperado is not None and (not isinstance(esperado, int) or isinstance(esperado, bool)):
            return jsonify(mensagem="Identificador de senha inválido."), 400
        corpo = json.dumps(dados, sort_keys=True, ensure_ascii=False)
        agora = relogio()
        with closing(conectar(caminho)) as banco:
            # A leitura e a alteração fazem parte da mesma transação de escrita.
            banco.execute("BEGIN IMMEDIATE")
            anterior = banco.execute("SELECT * FROM eventos WHERE requisicao=?", (requisicao,)).fetchone()
            if anterior:
                if anterior["corpo"] != corpo:
                    banco.rollback()
                    return jsonify(mensagem="Requisição já utilizada com outros dados."), 409
                resposta = estado(banco, agora)
                resposta.update(mensagem=anterior["detalhe"], repetida=True)
                banco.commit()
                return jsonify(resposta), anterior["http_status"]
            ativo = banco.execute("SELECT * FROM senhas WHERE inicio IS NOT NULL AND conclusao IS NULL").fetchone()
            proximo = banco.execute("SELECT * FROM senhas WHERE inicio IS NULL ORDER BY id LIMIT 1").fetchone()
            senha_id = None
            status = 200
            if acao == "chegada":
                quantidade = banco.execute("SELECT COUNT(*) FROM senhas WHERE inicio IS NULL").fetchone()[0]
                if quantidade >= 1000:
                    mensagem, status = "Capacidade de 1.000 pessoas aguardando atingida.", 409
                else:
                    senha_id = banco.execute("INSERT INTO senhas (chegada) VALUES (?)", (agora,)).lastrowid
                    mensagem = f"Chegada registrada. Senha A{senha_id:03d}."
            elif acao == "iniciar":
                if ativo:
                    mensagem, status = "Já existe um atendimento em curso.", 409
                elif proximo is None:
                    mensagem, status = "Fila vazia. Nenhuma pessoa para chamar.", 409
                elif esperado != proximo["id"]:
                    mensagem, status = "A fila mudou. Atualize e tente novamente.", 409
                else:
                    senha_id = proximo["id"]
                    banco.execute("UPDATE senhas SET inicio=? WHERE id=?", (max(agora, proximo["chegada"]), senha_id))
                    mensagem = f"Atendimento da senha A{senha_id:03d} iniciado."
            else:
                if ativo is None:
                    mensagem, status = "Nenhum atendimento em curso. Conclusão bloqueada.", 409
                elif esperado != ativo["id"]:
                    mensagem, status = "O atendimento mudou. Atualize e tente novamente.", 409
                else:
                    senha_id = ativo["id"]
                    banco.execute("UPDATE senhas SET conclusao=? WHERE id=?", (max(agora, ativo["inicio"]), senha_id))
                    mensagem = f"Atendimento da senha A{senha_id:03d} concluído."
            banco.execute("INSERT INTO eventos (instante,acao,senha_id,resultado,detalhe,requisicao,corpo,http_status) VALUES (?,?,?,?,?,?,?,?)", (agora, acao, senha_id, "aceito" if status == 200 else "rejeitado", mensagem, requisicao, corpo, status))
            resposta = estado(banco, agora)
            resposta.update(mensagem=mensagem, repetida=False)
            banco.commit()
        return jsonify(resposta), status

    @app.errorhandler(sqlite3.OperationalError)
    def erro_banco(erro):
        app.logger.exception("Falha de acesso ao SQLite")
        return jsonify(mensagem="Banco temporariamente indisponível. Atualize o painel antes de tentar novamente."), 503

    app.config["CAMINHO_BANCO"] = str(caminho)
    return app


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description="Citizen Assist AI - fila virtual")
    argumentos.add_argument("--host", default="127.0.0.1")
    argumentos.add_argument("--port", type=int, default=5000)
    argumentos.add_argument("--banco", type=Path)
    args = argumentos.parse_args()
    print(f"Painel disponível em http://{args.host}:{args.port}", flush=True)
    serve(criar_app(args.banco), host=args.host, port=args.port, threads=4)
