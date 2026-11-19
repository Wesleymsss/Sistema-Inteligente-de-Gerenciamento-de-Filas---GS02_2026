let estadoAtual = null;
let enviando = false;
const elemento = (id) => document.getElementById(id);
const minutos = (valor) => Number(valor).toLocaleString("pt-BR", {minimumFractionDigits: 1, maximumFractionDigits: 1});
const hora = (valor) => new Date(valor).toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit", second: "2-digit"});
const nomesAcoes = {chegada: "Chegada", iniciar: "Início", concluir: "Conclusão"};

function atualizarTela(estado) {
  estadoAtual = estado;
  elemento("aguardando").textContent = estado.aguardando;
  elemento("espera").textContent = minutos(estado.espera_ia_min);
  elemento("espera-media").textContent = minutos(estado.espera_media_min);
  elemento("concluidos").textContent = estado.concluidos;
  elemento("senha-atual").textContent = estado.em_atendimento?.senha || "Livre";
  elemento("inicio-atual").textContent = estado.em_atendimento ? "Início às " + hora(estado.em_atendimento.inicio) : "Aguardando a próxima chamada";
  elemento("atualizacao").textContent = "Atualizado às " + hora(estado.atualizado_em);
  elemento("origem-media").textContent = `${estado.origem_media}. Média atual de ${minutos(estado.media_atendimento_min)} minutos.`;
  elemento("faixa-modelo").textContent = estado.fora_faixa_treino ? "O tamanho atual da fila ultrapassa a faixa observada no treino. A previsão é uma extrapolação." : "";
  elemento("proximas").replaceChildren();
  if (!estado.proximas.length) {
    const item = document.createElement("li");
    item.textContent = "Nenhuma pessoa aguardando";
    elemento("proximas").append(item);
  }
  for (const senha of estado.proximas) {
    const item = document.createElement("li");
    const codigo = document.createElement("strong");
    const horario = document.createElement("span");
    codigo.textContent = senha.senha;
    horario.textContent = hora(senha.chegada);
    item.append(codigo, horario);
    elemento("proximas").append(item);
  }
  elemento("eventos").replaceChildren();
  for (const evento of estado.eventos) {
    const linha = document.createElement("tr");
    for (const texto of [hora(evento.horario), nomesAcoes[evento.acao] || evento.acao, evento.senha, evento.resultado === "aceito" ? "Registrado" : "Bloqueado"]) {
      const celula = document.createElement("td");
      celula.textContent = texto;
      linha.append(celula);
    }
    linha.lastChild.className = evento.resultado === "aceito" ? "accepted" : "rejected";
    linha.title = evento.detalhe;
    elemento("eventos").append(linha);
  }
  elemento("conexao").textContent = "Sistema conectado";
  elemento("conexao").classList.remove("offline");
}

async function consultar() {
  if (enviando) return;
  try {
    const resposta = await fetch("/api/estado", {cache: "no-store", signal: AbortSignal.timeout(8000)});
    if (!resposta.ok) throw new Error("Falha ao consultar a fila");
    const estado = await resposta.json();
    if (!enviando) atualizarTela(estado);
  } catch (erro) {
    elemento("conexao").textContent = "Sem conexão · tentando reconectar";
    elemento("conexao").classList.add("offline");
  }
}

async function executar(acao) {
  if (enviando || !estadoAtual) return;
  enviando = true;
  document.querySelectorAll("button").forEach((botao) => {botao.disabled = true;});
  const senhaId = acao === "iniciar" ? estadoAtual.proximas[0]?.id : estadoAtual.em_atendimento?.id;
  // O mesmo comando pode ser reenviado pela API com esta chave sem duplicar o evento.
  const requisicao = Array.from(crypto.getRandomValues(new Uint8Array(16)), (n) => n.toString(16).padStart(2, "0")).join("");
  try {
    const resposta = await fetch("/api/acao", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({acao, requisicao, senha_id: senhaId ?? null}),
      signal: AbortSignal.timeout(12000)
    });
    const resultado = await resposta.json();
    if (resultado.aguardando !== undefined) atualizarTela(resultado);
    elemento("mensagem").textContent = resultado.mensagem || "Operação indisponível.";
    elemento("mensagem").classList.toggle("erro", !resposta.ok);
  } catch (erro) {
    elemento("mensagem").textContent = "A conexão foi interrompida. Confira o histórico atualizado antes de repetir a operação.";
    elemento("mensagem").classList.add("erro");
    elemento("conexao").textContent = "Sem conexão";
    elemento("conexao").classList.add("offline");
  } finally {
    enviando = false;
    document.querySelectorAll("button").forEach((botao) => {botao.disabled = false;});
    consultar();
  }
}

elemento("chegada").addEventListener("click", () => executar("chegada"));
elemento("iniciar").addEventListener("click", () => executar("iniciar"));
elemento("concluir").addEventListener("click", () => executar("concluir"));
consultar();
setInterval(consultar, 3000);
fetch("/api/modelo").then((r) => r.json()).then((m) => {
  elemento("metricas-modelo").textContent = `Avaliação em ${m.amostras_teste} exemplos simulados de sessões separadas do treino. Erro médio da referência de ${minutos(m.mae_media_min)} min e da regressão de ${minutos(m.mae_ia_min)} min.`;
}).catch(() => {elemento("metricas-modelo").textContent = "Avaliação do modelo indisponível no momento.";});
