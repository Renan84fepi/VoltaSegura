"use strict";
// Utilidades compartilhadas pelas telas do cliente e do motorista.
const VS = (() => {
  const INTERVALO_POLLING = 4000; // RNF05: atualização a cada poucos segundos

  class ErroApi extends Error {
    constructor(mensagem, status) {
      super(mensagem);
      this.status = status;
    }
  }

  function csrf() {
    const achado = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return achado ? decodeURIComponent(achado[1]) : "";
  }

  function mensagemDeErro(corpo, status) {
    if (corpo && corpo.detail) return corpo.detail;
    if (corpo && typeof corpo === "object") {
      const mensagens = Object.values(corpo).flat();
      if (mensagens.length) return String(mensagens[0]);
    }
    if (status === 403) return "Você não tem permissão para esta ação.";
    return "Algo deu errado. Tente novamente.";
  }

  // Fetch com JSON e CSRF. Erros viram ErroApi com mensagem em português.
  async function api(url, { metodo = "GET", dados } = {}) {
    const opcoes = { method: metodo, credentials: "same-origin", headers: { Accept: "application/json" } };
    if (metodo !== "GET") {
      opcoes.headers["X-CSRFToken"] = csrf();
      opcoes.headers["Content-Type"] = "application/json";
      opcoes.body = JSON.stringify(dados || {});
    }
    let resposta;
    try {
      resposta = await fetch(url, opcoes);
    } catch {
      throw new ErroApi("Sem conexão. Tentando novamente…", 0);
    }
    const corpo = resposta.status === 204 ? null : await resposta.json().catch(() => null);
    if (!resposta.ok) throw new ErroApi(mensagemDeErro(corpo, resposta.status), resposta.status);
    return corpo;
  }

  // Executa `tarefa` agora e repete a cada `intervalo` ms. Devolve uma função para parar.
  function repetir(tarefa, intervalo = INTERVALO_POLLING) {
    let ativo = true;
    let timer;
    async function rodada() {
      try {
        await tarefa();
      } catch (erro) {
        console.warn(erro);
      }
      if (ativo) timer = setTimeout(rodada, intervalo);
    }
    rodada();
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }

  // RNF14: valores no padrão brasileiro.
  const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const umaCasa = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const dinheiro = (valor) => reais.format(Number(valor));
  function distancia(km) {
    const n = Number(km);
    return n < 1 ? `${Math.round(n * 1000)} m` : `${umaCasa.format(n)} km`;
  }
  const hora = (iso) => new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  // Evita injeção de HTML ao montar cards com template strings.
  function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  }

  // RNF04: mensagens para cada falha da Geolocation API.
  function mensagemGps(erro) {
    if (!erro || erro.code === undefined) return "Seu navegador não oferece localização.";
    if (erro.code === 1) return "Permissão de localização negada. Libere nas configurações do navegador.";
    if (erro.code === 2) return "Não foi possível obter a localização (GPS indisponível).";
    return "A localização demorou demais. Tente de novo.";
  }

  function posicaoAtual() {
    return new Promise((resolver, rejeitar) => {
      if (!("geolocation" in navigator)) return rejeitar(new Error(mensagemGps(null)));
      navigator.geolocation.getCurrentPosition(
        (p) => resolver({ latitude: p.coords.latitude, longitude: p.coords.longitude }),
        (erro) => rejeitar(new Error(mensagemGps(erro))),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
      );
    });
  }

  const ETAPAS = [
    ["solicitada", "Solicitada"],
    ["aceita", "Aceita"],
    ["a_caminho", "Motorista a caminho"],
    ["chegou", "Motorista chegou"],
    ["em_andamento", "Em andamento"],
    ["finalizada", "Finalizada"],
  ];

  // Lista das etapas da corrida, marcando as já feitas e a atual (RN04).
  function etapasHtml(status) {
    const atual = ETAPAS.findIndex(([chave]) => chave === status);
    return `<ol class="etapas">${ETAPAS.map(([, texto], i) => {
      const classe = i < atual ? "feita" : i === atual ? "atual" : "";
      const marca = i < atual ? "✔" : i === atual ? "●" : "○";
      return `<li class="${classe}">${marca} ${esc(texto)}</li>`;
    }).join("")}</ol>`;
  }

  function mostrarAlerta(elemento, mensagem, tipo = "danger") {
    elemento.className = `alert alert-${tipo}`;
    elemento.textContent = mensagem;
    elemento.hidden = !mensagem;
  }

  return { api, ErroApi, repetir, dinheiro, distancia, hora, esc, mensagemGps, posicaoAtual, etapasHtml, mostrarAlerta };
})();
