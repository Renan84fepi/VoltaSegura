"use strict";
// Painel do motorista (M2–M4): online/offline, localização, ofertas e corrida ativa.
(() => {
  const raiz = document.getElementById("trabalho");
  if (!raiz) return;
  const $ = (id) => document.getElementById(id);
  const urls = raiz.dataset;
  const urlCorrida = (id, acao = "") => urls.urlCorrida.replace("/0/", `/${id}/`) + (acao ? `${acao}/` : "");
  const ENVIO_LOCALIZACAO = 10000; // RF07: posição enviada a cada 10 s

  let situacao = null;
  let corridaChave = null; // "id:status" desenhado; evita apagar o código enquanto é digitado
  let ofertasChave = null;
  let ultimaPosicao = null; // do GPS ou do simulador
  let corridaAtual = null;
  let vigiaGps = null;
  let timerEnvio = null;

  const simulando = () => $("sim-ativo")?.checked;
  const aviso = (mensagem, tipo = "danger") => VS.mostrarAlerta($("aviso"), mensagem, tipo);
  const avisoGps = (mensagem, classe = "text-muted") => {
    $("aviso-gps").className = `small mt-2 ${classe}`;
    $("aviso-gps").textContent = mensagem;
  };

  // ---------------------------------------------------------- localização (RF07, RNF04)
  async function enviarPosicao() {
    if (simulando()) {
      ultimaPosicao = { latitude: Number($("sim-lat").value), longitude: Number($("sim-lng").value) };
    }
    if (!ultimaPosicao) return;
    try {
      await VS.api(urls.urlLocalizacao, { metodo: "POST", dados: ultimaPosicao });
    } catch (e) {
      if (e.status !== 409) avisoGps(e.message, "text-danger"); // 409 = ficou offline
    }
  }

  function iniciarLocalizacao() {
    if (timerEnvio) return;
    if (!simulando()) {
      if (!("geolocation" in navigator)) {
        avisoGps(VS.mensagemGps(null), "text-danger");
      } else {
        vigiaGps = navigator.geolocation.watchPosition(
          (p) => {
            ultimaPosicao = { latitude: p.coords.latitude, longitude: p.coords.longitude };
            avisoGps(`Localização ativa (${VS.hora(new Date().toISOString())}).`, "text-success");
          },
          (erro) => avisoGps(`${VS.mensagemGps(erro)} Sem localização você não recebe ofertas.`, "text-danger"),
          { enableHighAccuracy: true, timeout: 20000, maximumAge: 5000 }
        );
      }
    }
    enviarPosicao();
    timerEnvio = setInterval(enviarPosicao, ENVIO_LOCALIZACAO);
  }

  function pararLocalizacao() {
    if (vigiaGps !== null) navigator.geolocation.clearWatch(vigiaGps);
    clearInterval(timerEnvio);
    vigiaGps = null;
    timerEnvio = null;
  }

  // ---------------------------------------------------------- online/offline (RF06, RN01)
  function desenharStatus() {
    const online = situacao.online;
    $("selo-online").className = `badge fs-6 ${online ? "text-bg-success" : "text-bg-secondary"}`;
    $("selo-online").textContent = online ? "ONLINE" : "OFFLINE";
    $("impedimentos").innerHTML = situacao.impedimentos.map((m) => `<li>${VS.esc(m)}</li>`).join("");
    const botao = $("btn-online");
    botao.className = `btn btn-lg w-100 ${online ? "btn-outline-secondary" : "btn-success"}`;
    botao.textContent = online ? "Ficar offline" : "Ficar online";
    // Com impedimento (RN01) ou em corrida, o botão fica desabilitado.
    botao.disabled = (!online && !situacao.pode_ficar_online) || (online && !!situacao.corrida_ativa);
  }

  $("btn-online").addEventListener("click", async () => {
    const botao = $("btn-online");
    botao.disabled = true;
    try {
      situacao = await VS.api(urls.urlDisponibilidade, { metodo: "POST", dados: { online: !situacao.online } });
      aviso("");
    } catch (e) {
      aviso(e.message);
    }
    await atualizar();
  });

  // ---------------------------------------------------------- ofertas (RF11, RF12)
  function desenharOfertas(ofertas) {
    const chave = ofertas.map((o) => o.id).join(",");
    if (chave === ofertasChave) return;
    ofertasChave = chave;
    if (!ofertas.length) {
      $("area-ofertas").innerHTML = situacao.online
        ? `<p class="text-muted text-center">Aguardando solicitações próximas…</p>`
        : "";
      return;
    }
    $("area-ofertas").innerHTML = ofertas.map((o) => `
      <div class="card mb-3 border-success"><div class="card-body">
        <h2 class="h5">Nova corrida!</h2>
        <p class="mb-1">Coleta a <strong>${VS.distancia(o.distancia_ate_coleta_km)}</strong> de você</p>
        <p class="mb-1 small"><strong>De:</strong> ${VS.esc(o.origem_endereco)}</p>
        <p class="mb-1 small"><strong>Para:</strong> ${VS.esc(o.destino_endereco)} (${VS.distancia(o.distancia_km)})</p>
        <p class="mb-1 small text-muted">${VS.esc(o.veiculo)} • ${VS.esc(o.forma_pagamento)}</p>
        <p class="fs-5 mb-2">Você recebe <strong>${VS.dinheiro(o.valor_motorista)}</strong></p>
        <div class="d-flex gap-2">
          <button class="btn btn-success btn-lg flex-fill" data-aceitar="${o.id}">Aceitar</button>
          <button class="btn btn-outline-danger btn-lg flex-fill" data-recusar="${o.id}">Recusar</button>
        </div>
      </div></div>`).join("");
  }

  $("area-ofertas").addEventListener("click", async (evento) => {
    const botao = evento.target.closest("button");
    if (!botao) return;
    const aceitar = botao.dataset.aceitar;
    const id = aceitar || botao.dataset.recusar;
    botao.disabled = true;
    try {
      await VS.api(urlCorrida(id, aceitar ? "aceitar" : "recusar"), { metodo: "POST" });
      aviso("");
    } catch (e) {
      aviso(e.status === 409 ? "Outro motorista aceitou primeiro." : e.message, "warning"); // RN03
    }
    ofertasChave = null;
    await atualizar();
  });

  // ---------------------------------------------------------- corrida ativa (RF13–RF17, RN04)
  function posicaoTexto(c) {
    const p = c.posicao_motorista;
    if (!p) return "Sem localização recente.";
    return `Você está a ${VS.distancia(p.distancia_km)} ${p.alvo === "coleta" ? "da coleta" : "do destino"}.`;
  }

  // Só o botão da próxima etapa válida aparece (RN04).
  function acoes(c) {
    if (c.status === "aceita") return `<button class="btn btn-primary btn-lg w-100 mb-2" data-acao="a-caminho">Estou a caminho</button>`;
    if (c.status === "a_caminho") return `<button class="btn btn-primary btn-lg w-100 mb-2" data-acao="chegou">Cheguei ao local</button>`;
    if (c.status === "chegou") {
      return `<label class="form-label fw-semibold" for="codigo">Código informado pelo cliente</label>
        <input id="codigo" class="form-control form-control-lg text-center codigo mb-1" inputmode="numeric"
               maxlength="4" autocomplete="off" placeholder="0000">
        <div class="form-text mb-2">Tentativas restantes: ${c.tentativas_restantes}</div>
        <button class="btn btn-success btn-lg w-100 mb-2" data-acao="iniciar">Iniciar corrida</button>`;
    }
    if (c.status === "em_andamento") return `<button class="btn btn-success btn-lg w-100 mb-2" data-acao="finalizar">Finalizar no destino</button>`;
    return "";
  }

  function desenharCorrida(c) {
    corridaAtual = c;
    const chave = c ? `${c.id}:${c.status}` : null;
    if (chave === corridaChave) {
      const campo = document.querySelector("[data-campo=posicao]");
      if (campo) campo.textContent = posicaoTexto(c);
      return;
    }
    corridaChave = chave;
    if (!c) {
      $("area-corrida").innerHTML = "";
      return;
    }
    $("area-corrida").innerHTML = `
      <div class="card mb-3 border-primary"><div class="card-body">
        <div class="d-flex justify-content-between"><h2 class="h5">Corrida #${c.id}</h2>
          <span class="badge text-bg-primary align-self-start">${VS.esc(c.status_texto)}</span></div>
        <div class="mb-2">${VS.etapasHtml(c.status)}</div>
        <div class="fw-bold">${VS.esc(c.cliente.nome)}</div>
        <div class="mb-2"><a href="tel:${VS.esc(c.cliente.telefone)}">${VS.esc(c.cliente.telefone)}</a></div>
        <div class="small"><strong>Coleta:</strong> ${VS.esc(c.origem_endereco)}</div>
        <div class="small"><strong>Destino:</strong> ${VS.esc(c.destino_endereco)}</div>
        <div class="small"><strong>Veículo:</strong> ${VS.esc(c.veiculo)}</div>
        <div class="small mb-2"><strong>Você recebe:</strong> ${VS.dinheiro(c.valor_motorista)} • ${VS.esc(c.forma_pagamento)}</div>
        <div class="fw-semibold mb-3" data-campo="posicao">${VS.esc(posicaoTexto(c))}</div>
        ${acoes(c)}
        ${c.pode_cancelar ? `<button class="btn btn-outline-danger w-100" data-acao="cancelar">Cancelar corrida</button>` : ""}
      </div></div>`;
    $("codigo")?.focus();
  }

  $("area-corrida").addEventListener("click", async (evento) => {
    const botao = evento.target.closest("button[data-acao]");
    if (!botao || !corridaAtual) return;
    const acao = botao.dataset.acao;
    let dados = {};
    if (acao === "iniciar") dados = { codigo: $("codigo").value.trim() };
    if (acao === "finalizar" && !confirm("Confirmar a chegada ao destino e finalizar a corrida?")) return;
    if (acao === "cancelar") {
      const motivo = prompt("Motivo do cancelamento:");
      if (!motivo) return;
      dados = { motivo };
    }
    botao.disabled = true;
    try {
      const c = await VS.api(urlCorrida(corridaAtual.id, acao), { metodo: "POST", dados });
      if (c.status === "finalizada") aviso(`Corrida #${c.id} finalizada. Você recebe ${VS.dinheiro(c.valor_motorista)}.`, "success");
      else if (c.status === "cancelada") aviso(`Corrida #${c.id} cancelada.`, "secondary");
      else aviso("");
    } catch (e) {
      aviso(e.message);
      if (acao === "iniciar") corridaChave = null; // redesenha para atualizar as tentativas
    }
    await atualizar();
  });

  // ---------------------------------------------------------- simulador (só com DEBUG)
  $("sim-ativo")?.addEventListener("change", () => {
    pararLocalizacao();
    if (situacao?.online || situacao?.corrida_ativa) iniciarLocalizacao();
    avisoGps(simulando() ? "Usando posição simulada." : "");
  });
  $("sim-enviar")?.addEventListener("click", () => {
    $("sim-ativo").checked = true;
    $("sim-ativo").dispatchEvent(new Event("change"));
  });
  $("sim-andar")?.addEventListener("click", () => {
    if (!corridaAtual) return aviso("Sem corrida ativa: não há para onde andar.", "warning");
    const alvo = corridaAtual.status === "em_andamento" ? corridaAtual.destino : corridaAtual.origem;
    const lat = Number($("sim-lat").value);
    const lng = Number($("sim-lng").value);
    $("sim-lat").value = (lat + (Number(alvo[0]) - lat) / 2).toFixed(6);
    $("sim-lng").value = (lng + (Number(alvo[1]) - lng) / 2).toFixed(6);
    $("sim-ativo").checked = true;
    pararLocalizacao();
    iniciarLocalizacao();
  });

  // ---------------------------------------------------------- polling (RF18, RNF05)
  async function atualizar() {
    try {
      situacao = await VS.api(urls.urlDisponibilidade);
      desenharStatus();
      if (situacao.online || situacao.corrida_ativa) iniciarLocalizacao();
      else pararLocalizacao();

      if (situacao.corrida_ativa) {
        desenharCorrida(await VS.api(urlCorrida(situacao.corrida_ativa)));
        ofertasChave = null;
        $("area-ofertas").innerHTML = "";
      } else {
        desenharCorrida(null);
        desenharOfertas(situacao.online ? await VS.api(urls.urlOfertas) : []);
      }
      if ($("aviso").textContent.startsWith("Sem conexão")) aviso("");
    } catch (e) {
      aviso(e.message, "warning");
    }
  }

  VS.repetir(atualizar);
})();
