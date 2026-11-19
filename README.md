# Citizen Assist AI

Este projeto simula a fila de uma biblioteca com um balcão. Você registra a chegada, chama a próxima senha e conclui o atendimento pelos botões do painel. O sistema salva os horários, conta as pessoas aguardando e compara duas estimativas de espera.

Este repositório reúne o código e os arquivos para executar e testar o sistema. O relatório, o diagrama, as imagens e o vídeo estão no ZIP de entregáveis fornecido à equipe. As instruções de execução estão neste README.

## Como abrir no computador

Você precisa de **Python 3.11 ou 3.12 de 64 bits** e de internet na primeira instalação.

1. No GitHub, clique em **Code** e depois em **Download ZIP**.
2. Extraia o arquivo e abra a pasta que contém `app.py` e `requirements.txt`.
3. Siga a seção **Instalação pelos comandos**, abaixo.
4. Com o programa rodando, abra [http://127.0.0.1:5000](http://127.0.0.1:5000) no navegador.

Deixe o terminal aberto enquanto usa o painel. Para encerrar, pressione `Ctrl+C`. Se a porta 5000 estiver ocupada, execute `python app.py --port 5001` e abra `http://127.0.0.1:5001`.

## Como testar os botões

1. Clique em **Registrar chegada** três vezes. As senhas A001, A002 e A003 entram na fila, se o banco estiver vazio.
2. Clique em **Iniciar atendimento**. A primeira senha vai para o balcão e restam duas pessoas aguardando.
3. Espere alguns segundos e clique em **Concluir atendimento**. O total de concluídos aumenta e a média é atualizada.
4. Atenda as outras duas senhas da mesma forma.
5. Tente concluir mais uma vez. O painel bloqueia a operação e registra a tentativa no histórico.

Os tempos desses testes são curtos, então a média local ficará baixa. A espera exibida vale para uma pessoa que chegar naquele momento. Se alguém estiver no balcão, pode haver espera mesmo com zero pessoas aguardando.

O painel se atualiza a cada três segundos. Para conferir isso, abra o mesmo endereço em outra aba e registre uma chegada na primeira. Para salvar os eventos, clique em **Baixar histórico CSV**.

## Arquivos principais

| Arquivo ou pasta | O que você encontra |
| --- | --- |
| `app.py` | Regras da fila, banco de dados e comunicação com o painel |
| `previsao.py` | Geração dos exemplos, treino e avaliação da previsão |
| `templates/` e `static/` | Arquivos da interface web |
| `dados/` | Exemplos simulados e avaliação do modelo |

O banco `dados/fila.sqlite3` é criado ao abrir o programa pela primeira vez. Os registros ficam salvos ao fechar o projeto. Para fazer uma apresentação começando do zero, use um banco com outro nome pelos comandos manuais.

```bash
python app.py --banco dados/apresentacao.sqlite3
```

## Instalação pelos comandos

Abra um terminal na pasta que contém `app.py`. Crie o ambiente Python.

```bash
python -m venv .venv
```

No Prompt de Comando do Windows, ative o ambiente com este comando.

```bat
.venv\Scripts\activate.bat
```

No Linux ou macOS, ative desta forma. Se o comando Python do seu computador for `python3`, use esse nome ao criar o ambiente.

```bash
source .venv/bin/activate
```

Com o ambiente ativo, instale as bibliotecas e abra o projeto.

```bash
python -m pip install -r requirements.txt
python app.py
```

## Como mostrar no celular

Para testar pelo mesmo Wi-Fi, abra o servidor com este comando.

```bash
python app.py --host 0.0.0.0
```

Encontre o IPv4 do computador nas configurações de rede ou com `ipconfig` no Windows. No celular, conectado ao mesmo Wi-Fi, abra `http://IP_DO_COMPUTADOR:5000`, trocando o trecho do IP pelo número encontrado. Se o Windows pedir, permita o acesso do Python pela rede privada.

Para demonstrar pela internet, instale o `cloudflared` conforme a [documentação oficial](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/). Deixe o projeto rodando e, em outro terminal, execute este comando.

```bash
cloudflared tunnel --url http://localhost:5000
```

Abra o link HTTPS gerado no terminal. Para conferir o acesso externo, use os dados móveis do celular, registre uma chegada no computador e veja a atualização no celular. O link funciona enquanto o programa e o túnel estiverem abertos. Qualquer pessoa com esse endereço pode usar os botões do protótipo.

O pacote inclui a verificação em duas sessões de navegador por HTTP local. A ativação e o teste do link externo ficam para o computador da apresentação.

## Como conferir os testes e a previsão

Se mantiver a pasta opcional `testes/`, execute os dez testes a partir da pasta principal, com o ambiente Python ativo.

```bash
python -m unittest discover -s testes -v
```

Eles verificam os quatro casos pedidos na atividade, além da ordem das senhas, dos registros após reinício e de operações simultâneas. Os testes usam bancos temporários.

Para treinar novamente com o CSV incluído e atualizar as métricas, execute este comando.

```bash
python previsao.py
```

O CSV contém **2.500 exemplos simulados** de 50 sessões. As primeiras 40 sessões formam o treino e as últimas 10 formam o teste. A média histórica teve erro médio de **2,0576 minutos** e a regressão linear, de **1,9288 minuto**, nos 500 exemplos de teste. O relatório técnico do ZIP de entregáveis explica as contas e os limites da simulação.

No painel, a média começa em cinco minutos como referência simulada. Depois, passa a usar os últimos cinco atendimentos concluídos. A regressão continua treinada com o CSV. Filas acima de 12 pessoas recebem um aviso porque ultrapassam o tamanho observado no treino.

Se mantiver o arquivo opcional `diagnostico.py`, você pode medir o computador da apresentação. Deixe o sistema aberto e rode `python diagnostico.py` em outro terminal com o ambiente ativo. O resultado fica em `dados/diagnostico_local.json`. Para medir também a RAM do processo, acrescente `--pid NUMERO_DO_PROCESSO`, usando o PID mostrado no Gerenciador de Tarefas.

## Como enviar o trabalho

Inclua o link deste repositório na entrega junto com o relatório, o diagrama e o vídeo do ZIP de entregáveis. O `.gitignore` exclui o ambiente Python e o banco com os registros locais.

O ZIP de entregáveis também contém as capturas, a tabela verdade e o guia do circuito montado no Logicly. A versão online usada na montagem restringiu a exportação do arquivo nativo `.logicly`.

## Documentação usada

- [Flask com Waitress](https://flask.palletsprojects.com/en/stable/deploying/waitress/)
- [SQLite em Python](https://docs.python.org/3/library/sqlite3.html)
- [Regressão linear](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html)
- [Erro absoluto médio](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html)
- [Logicly](https://logic.ly/demo/)
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
