"""Execute com python -m unittest discover -s testes -v."""

import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app import criar_app


class TesteFila(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "teste.sqlite3"
        self.agora = 1_800_000_000.0
        self.app = criar_app(self.caminho, lambda: self.agora)
        self.cliente = self.app.test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def acao(self, nome, senha=None, chave=None):
        return self.cliente.post("/api/acao", json={"acao": nome, "senha_id": senha, "requisicao": chave or uuid.uuid4().hex})

    def estado(self):
        return self.cliente.get("/api/estado").get_json()

    def test_chegadas_e_fifo(self):
        for _ in range(3):
            self.assertEqual(self.acao("chegada").status_code, 200)
        self.assertEqual(self.estado()["aguardando"], 3)
        self.assertEqual(self.acao("iniciar", 1).get_json()["em_atendimento"]["id"], 1)
        self.assertEqual(self.estado()["aguardando"], 2)

    def test_conclusao_e_duracao(self):
        self.acao("chegada")
        self.acao("iniciar", 1)
        self.agora += 180
        self.assertEqual(self.acao("concluir", 1).status_code, 200)
        self.assertEqual(self.estado()["concluidos"], 1)
        self.assertEqual(self.estado()["media_atendimento_min"], 3.0)

    def test_saida_com_fila_vazia(self):
        resposta = self.acao("concluir")
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(self.estado()["aguardando"], 0)
        self.assertEqual(self.estado()["concluidos"], 0)
        self.assertEqual(self.estado()["eventos"][0]["resultado"], "rejeitado")

    def test_previsao_muda_com_fila(self):
        self.assertEqual(self.estado()["espera_ia_min"], 0)
        self.acao("chegada")
        antes = self.estado()
        self.acao("chegada")
        depois = self.estado()
        self.assertGreater(depois["espera_ia_min"], antes["espera_ia_min"])
        self.assertGreater(depois["espera_media_min"], antes["espera_media_min"])

    def test_persistencia(self):
        self.acao("chegada")
        outro = criar_app(self.caminho).test_client()
        self.assertEqual(outro.get("/api/estado").get_json()["aguardando"], 1)

    def test_reenvio_sem_duplicacao(self):
        chave = uuid.uuid4().hex
        self.acao("chegada", chave=chave)
        self.assertTrue(self.acao("chegada", chave=chave).get_json()["repetida"])
        self.assertEqual(self.estado()["aguardando"], 1)
        self.assertEqual(len(self.estado()["eventos"]), 1)
        self.assertEqual(self.acao("iniciar", 1, chave).status_code, 409)

    def test_balcao_e_senha_desatualizada(self):
        self.acao("chegada")
        self.acao("chegada")
        self.acao("iniciar", 1)
        self.assertEqual(self.acao("iniciar", 2).status_code, 409)
        self.assertEqual(self.acao("concluir", 2).status_code, 409)
        self.assertEqual(self.estado()["em_atendimento"]["id"], 1)

    def test_concorrencia(self):
        def registrar(_):
            with self.app.test_client() as cliente:
                return cliente.post("/api/acao", json={"acao": "chegada", "requisicao": uuid.uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=5) as executor:
            self.assertTrue(all(c == 200 for c in executor.map(registrar, range(20))))
        self.assertEqual(self.estado()["aguardando"], 20)
        self.acao("iniciar", 1)
        def finalizar(_):
            with self.app.test_client() as cliente:
                return cliente.post("/api/acao", json={"acao": "concluir", "senha_id": 1, "requisicao": uuid.uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sorted(executor.map(finalizar, range(2))), [200, 409])
        self.assertEqual(self.estado()["concluidos"], 1)

    def test_json_invalido_e_exportacao(self):
        self.assertEqual(self.cliente.post("/api/acao", json=[]).status_code, 400)
        self.acao("chegada")
        self.assertIn("chegada", self.cliente.get("/api/eventos.csv").get_data(as_text=True))

    def test_iniciar_vazia(self):
        self.assertEqual(self.acao("iniciar").status_code, 409)
        self.assertIsNone(self.estado()["em_atendimento"])


if __name__ == "__main__":
    unittest.main()
