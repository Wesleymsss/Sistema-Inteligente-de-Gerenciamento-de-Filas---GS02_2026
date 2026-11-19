# Sistema Inteligente de Gerenciamento de Filas Virtuais

Citizen Assist AI · Computer Organization and Architecture · 1CC-FEV

Protótipo de atendimento em uma biblioteca, com um balcão, senhas por ordem de chegada, previsão de espera e registros persistentes. A aplicação usa o processador, a RAM, o armazenamento e a rede do computador em que é executada. O circuito montado no Logicly demonstra a regra de autorização da conclusão de atendimento.

## Instalação e execução

Use Python 3.11 ou 3.12 de 64 bits. Na primeira instalação, é necessária internet para baixar as dependências. Extraia o ZIP antes de executar.

No Windows, abra a pasta no Explorador e execute `iniciar_windows.bat`. Ele cria o ambiente Python e instala as dependências na primeira execução. Quando aparecer a mensagem do servidor, abra http://127.0.0.1:5000 no navegador. Mantenha o terminal aberto. Se usar outro ambiente, siga os comandos abaixo.

```bash
python -m venv .venv
```

Ative o ambiente no Windows pelo Prompt de Comando.

```bat
.venv\Scripts\activate.bat
```

No Linux ou macOS, ative desta forma.

```bash
source .venv/bin/activate
```

Com o ambiente ativo, instale e execute.

```bash
python -m pip install -r requirements.txt
python app.py
```

O SQLite cria `dados/fila.sqlite3` automaticamente. Os exemplos de treino ficam em um CSV separado e possuem a origem `simulado`. Os registros do painel ficam somente no banco local.

## Uso do painel

1. Clique em **Registrar chegada** para emitir uma senha.
2. Clique em **Iniciar atendimento** para chamar a senha mais antiga. A pessoa sai da contagem de aguardando e passa para o balcão.
3. Ao terminar o serviço, clique em **Concluir atendimento**. O sistema mede a duração entre início e conclusão e atualiza a média recente.
4. Tente concluir novamente. A operação é bloqueada e aparece no histórico.
5. Use **Baixar histórico CSV** para guardar todos os eventos. A tela mostra os 12 mais recentes.

O indicador de espera representa o tempo até o início do atendimento de uma pessoa que chegar naquele momento. Uma fila sem pessoas aguardando pode ter espera positiva se o balcão estiver ocupado. O atendimento é FIFO, sem prioridades e com capacidade de até 1.000 pessoas aguardando.

## Rede e acesso pela internet

Para testar dois dispositivos na mesma rede, execute o servidor ouvindo todas as interfaces.

```bash
python app.py --host 0.0.0.0
```

Descubra o IPv4 do computador com `ipconfig` no Windows ou nas configurações de rede do sistema. No celular conectado ao mesmo Wi-Fi, abra `http://IP_DO_COMPUTADOR:5000`, substituindo o IP pelo valor encontrado. Se solicitado pelo sistema operacional, permita o servidor na rede privada.

Para disponibilizar a demonstração pela internet, instale o `cloudflared` da página oficial https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/ e mantenha `python app.py` em execução. Em outro terminal, execute o comando a seguir.

```bash
cloudflared tunnel --url http://localhost:5000
```

Abra no celular o endereço HTTPS `trycloudflare.com` impresso no terminal, preferencialmente usando os dados móveis para demonstrar o acesso externo. Registre uma chegada no computador e observe a mudança no celular em aproximadamente três segundos. O link é temporário e depende do computador e do túnel ligados. Esta opção é adequada à demonstração acadêmica. O protótipo usa controle aberto, portanto qualquer visitante do link pode acionar os botões.

A entrega contém testes locais da API. A ativação e a verificação do túnel público são feitas no computador da apresentação. Não há URL pública permanente provisionada neste pacote.

## Testes e reprodução dos resultados

Execute os testes a partir da raiz do projeto.

```bash
python -m unittest discover -s testes -v
```

Os testes usam arquivos temporários, um relógio controlado e bancos independentes. Eles verificam chegadas, FIFO, início, conclusão, duração, saída com fila vazia, previsão, persistência, requisições repetidas, concorrência e exportação. Os horários controlados dos testes representam uma simulação. Os cliques do painel recebem o horário UTC real do servidor, convertido para a hora local na tela.

Para recalcular as métricas da regressão e salvar o JSON.

```bash
python previsao.py
```

Para gerar o CSV novamente, sem alterar o banco da fila.

```bash
python -c "from previsao import gerar_historico, BASE; gerar_historico(BASE / 'dados' / 'historico_simulado.csv')"
```

Para medir o computador em que o servidor está rodando.

```bash
python diagnostico.py
```

O diagnóstico grava informações do ambiente e a latência de 50 consultas HTTP locais em `dados/diagnostico_local.json`. Para incluir o consumo de RAM do servidor, acrescente `--pid NUMERO_DO_PROCESSO`, usando o PID observado no Gerenciador de Tarefas ou monitor de processos.

Para começar uma demonstração com um banco novo, escolha outro nome de arquivo.

```bash
python app.py --banco dados/apresentacao.sqlite3
```

## Previsão e origem dos dados

O arquivo `dados/historico_simulado.csv` contém 2.500 observações de 50 sessões simuladas, com semente aleatória 2026. Cada sessão tem 50 chegadas, intervalos exponenciais com média de 6 minutos e durações gaussianas truncadas em 0,5 minuto. O ritmo médio varia entre 3 e 7 minutos por sessão e o desvio padrão das durações é de 1,3 minuto.

A cada chegada são calculados o número de pessoas aguardando, a média dos últimos cinco serviços concluídos e o residual estimado do serviço em andamento. O alvo é a espera até o início do atendimento daquela pessoa. As sessões 0 a 39 formam o treino, com 2.000 exemplos, e as sessões 40 a 49 formam o teste, com 500. A separação por sessão evita misturar observações da mesma fila nos dois conjuntos.

A referência convencional calcula `aguardando × média_recente + residual`. A regressão usa `aguardando`, `aguardando × média_recente` e `residual`, com intercepto e mínimos quadrados. As duas previsões são limitadas a zero. Quando não há espera nem residual, ambas exibem zero. O residual é `máximo(média_recente − tempo_decorrido, 0)` para um serviço em curso. Essa aproximação pode subestimar um serviço que já ultrapassou sua média.

No teste incluído, o MAE foi de 2,0576 minutos para a referência e 1,9288 minuto para a regressão. Os resultados descrevem o simulador e precisam de nova avaliação com dados de atendimento real. A tela usa a referência inicial de cinco minutos até existirem conclusões locais e depois calcula a média dos últimos cinco serviços. O modelo permanece treinado com o CSV simulado. Filas acima de 12 pessoas geram aviso de extrapolação.

## Organização dos arquivos

| Caminho | Conteúdo |
| --- | --- |
| `app.py` | API Flask, transações SQLite e servidor Waitress |
| `previsao.py` | Simulação, treino e comparação das estimativas |
| `templates/` e `static/` | Painel web e atualização a cada três segundos |
| `dados/` | Histórico simulado e métricas do modelo |
| `testes/` | Testes automatizados reproduzíveis |
| `diagnostico.py` | Medição do ambiente e da comunicação local |
| `documentacao/` | Relatório, arquitetura, guia Logicly e demonstração |
| `documentacao/evidencias/` | Capturas reais e resultados dos testes |

## Publicação do código

Crie um repositório no GitHub pelo seu perfil, envie esta pasta e inclua o link no envio da atividade. O arquivo `.gitignore` já exclui o ambiente Python e o banco de operações locais. Mantenha o CSV simulado, os testes e a documentação no repositório. O pacote está organizado para publicação, e o envio à sua conta é feito por você.

## Referências

- Flask e Waitress — https://flask.palletsprojects.com/en/stable/deploying/waitress/
- SQLite em Python — https://docs.python.org/3/library/sqlite3.html
- Regressão linear — https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html
- Erro absoluto médio — https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html
- Logicly — https://logic.ly/demo/
- Cloudflare Quick Tunnels — https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
