"use strict";
// Telas do cliente: solicitar (C2/C3) e acompanhar (C4).

// ------------------------------------------------------------ solicitar
(() => {
  const raiz = document.getElementById("pedido");
  if (!raiz) return;
  const $ = (id) => document.getElementById(id);
  const origem = $("origem");
  const destino = $("destino");
  let posicaoAparelho = null; // RF09: coordenadas do GPS, se o cliente usar
  let estimativa = null; // resposta da API, com coordenadas já resolvidas

  // Editou o endereço à mão: descarta a posição do aparelho.
  origem.addEventListener("input", () => {
    posicaoAparelho = null;
    $("aviso-gps").textContent = "";
  });

  $("usar-posicao").addEventListener("click", async () => {
    const aviso = $("aviso-gps");
    aviso.className = "form-text";
    aviso.textContent = "Obtendo sua localização…";
    try {
      posicaoAparelho = await VS.posicaoAtual();
      origem.value = "Minha localização atual";
      aviso.className = "form-text text-success";
      aviso.textContent = "Localização obtida.";
    } catch (erro) {
      posicaoAparelho = null;
      aviso.className = "form-text text-danger";
      aviso.textContent = `${erro.message} Digite o endereço de coleta.`; // RNF04
    }
  });

  function pontos() {
    return {
      origem_endereco: origem.value.trim(),
      origem_latitude: posicaoAparelho?.latitude ?? null,
      origem_longitude: posicaoAparelho?.longitude ?? null,
      destino_endereco: destino.value.trim(),
    };
  }

  $("form-pedido").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const erro = $("erro");
    VS.mostrarAlerta(erro, "");
    if (!origem.value.trim() || !destino.value.trim()) {
      return VS.mostrarAlerta(erro, "Informe a coleta e o destino.");
    }
    const botao = $("btn-estimar");
    botao.disabled = true;
    botao.textContent = "Calculando…";
    try {
      estimativa = await VS.api(raiz.dataset.urlEstimativa, { metodo: "POST", dados: pontos() });
      $("conf-distancia").textContent = VS.distancia(estimativa.distancia_km);
      $("conf-preco").textContent = VS.dinheiro(estimativa.preco_estimado);
      $("conf-trajeto").textContent = `${origem.value.trim()} → ${destino.value.trim()}`;
      const forma = document.querySelector("input[name=forma_pagamento]:checked");
      $("conf-veiculo").textContent =
        `${$("veiculo").selectedOptions[0].textContent} • ${forma.parentElement.textContent.trim()}`;
      VS.mostrarAlerta($("erro-confirmacao"), "");
      $("form-pedido").hidden = true;
      $("confirmacao").hidden = false;
    } catch (e) {
      VS.mostrarAlerta(erro, e.message);
    } finally {
      botao.disabled = false;
      botao.textContent = "Ver estimativa";
    }
  });

  $("btn-voltar").addEventListener("click", () => {
    $("confirmacao").hidden = true;
    $("form-pedido").hidden = false;
  });

  $("btn-confirmar").addEventListener("click", async () => {
    const botao = $("btn-confirmar");
    botao.disabled = true;
    try {
      const corrida = await VS.api(raiz.dataset.urlSolicitar, {
        metodo: "POST",
        dados: {
          ...pontos(),
          // Reaproveita as coordenadas da estimativa: o servidor recalcula o preço.
          origem_latitude: estimativa.origem_latitude,
          origem_longitude: estimativa.origem_longitude,
          destino_latitude: estimativa.destino_latitude,
          destino_longitude: estimativa.destino_longitude,
          veiculo: $("veiculo").value,
          forma_pagamento: document.querySelector("input[name=forma_pagamento]:checked").value,
        },
      });
      location.href = raiz.dataset.urlAcompanhar.replace("/0/", `/${corrida.id}/`);
    } catch (e) {
      VS.mostrarAlerta($("erro-confirmacao"), e.message);
      botao.disabled = false;
    }
  });
})();

// ------------------------------------------------------------ acompanhar
(() => {
  const raiz = document.getElementById("acompanhamento");
  if (!raiz) return;
  const painel = document.getElementById("painel-corrida");
  const aviso = document.getElementById("aviso-conexao");
  let chave = null; // status desenhado; só redesenha quando muda
  let parar = null;

  function posicaoTexto(corrida) {
    const p = corrida.posicao_motorista;
    if (!p) return "Aguardando a localização do motorista…";
    const alvo = p.alvo === "coleta" ? "do local de coleta" : "do destino";
    const quando = p.atualizada_em ? ` (atualizado às ${VS.hora(p.atualizada_em)})` : "";
    return `Motorista a ${VS.distancia(p.distancia_km)} ${alvo}${quando}`;
  }

  function desenhar(c) {
    const m = c.motorista;
    const final = c.status === "finalizada" || c.status === "cancelada";
    let html = "";
    if (c.status === "cancelada") {
      html += `<div class="alert alert-secondary"><strong>Corrida cancelada.</strong>
        ${c.motivo_cancelamento ? `<br>Motivo: ${VS.esc(c.motivo_cancelamento)}` : ""}</div>`;
    } else if (c.status === "finalizada") {
      html += `<div class="alert alert-success"><strong>Corrida finalizada!</strong><br>
        Valor: ${VS.dinheiro(c.preco_estimado)} • ${VS.esc(c.forma_pagamento)}</div>`;
    } else {
      html += `<div class="card mb-3"><div class="card-body">${VS.etapasHtml(c.status)}</div></div>`;
    }
    if (c.status === "solicitada") {
      html += `<div class="alert alert-info d-flex align-items-center gap-2">
        <span class="spinner-border spinner-border-sm"></span> Procurando um motorista próximo…</div>`;
    }
    if (c.codigo_confirmacao) {
      // RF15: o cliente informa o código; sem ele o motorista não inicia a corrida.
      html += `<div class="card mb-3 border-primary"><div class="card-body text-center">
        <div class="small text-muted">Informe este código ao motorista na chegada</div>
        <div class="codigo">${VS.esc(c.codigo_confirmacao)}</div></div></div>`;
    }
    if (m && !final) {
      html += `<div class="card mb-3"><div class="card-body">
        <h2 class="h6 mb-2">Seu motorista</h2>
        <div class="fw-bold">${VS.esc(m.nome)}</div>
        <div><a href="tel:${VS.esc(m.telefone)}">${VS.esc(m.telefone)}</a></div>
        ${m.bicicleta ? `<div class="small text-muted">Bicicleta: ${VS.esc(m.bicicleta)}
          (<a href="${VS.esc(m.foto_bicicleta)}" target="_blank" rel="noopener">ver foto</a>)</div>` : ""}
        <div class="mt-2 fw-semibold" data-campo="posicao">${VS.esc(posicaoTexto(c))}</div>
      </div></div>`;
    }
    html += `<div class="card mb-3"><div class="card-body small">
      <div><strong>Coleta:</strong> ${VS.esc(c.origem_endereco)}</div>
      <div><strong>Destino:</strong> ${VS.esc(c.destino_endereco)}</div>
      <div><strong>Veículo:</strong> ${VS.esc(c.veiculo)}</div>
      <div><strong>Distância:</strong> ${VS.distancia(c.distancia_km)} •
        <strong>Estimativa:</strong> ${VS.dinheiro(c.preco_estimado)} • ${VS.esc(c.forma_pagamento)}</div>
    </div></div>`;
    if (c.pode_cancelar) {
      html += `<button id="btn-cancelar" class="btn btn-outline-danger btn-lg w-100">Cancelar corrida</button>`;
    }
    if (final) {
      html += `<a class="btn btn-primary btn-lg w-100" href="${VS.esc(raiz.dataset.urlNova)}">Nova corrida</a>`;
    }
    painel.innerHTML = html;
    document.getElementById("btn-cancelar")?.addEventListener("click", cancelar);
  }

  async function cancelar() {
    if (!confirm("Cancelar esta corrida?")) return;
    try {
      desenhar(await VS.api(raiz.dataset.urlCancelar, { metodo: "POST", dados: {} }));
    } catch (e) {
      VS.mostrarAlerta(aviso, e.message);
    }
  }

  async function atualizar() {
    let corrida;
    try {
      corrida = await VS.api(raiz.dataset.urlCorrida);
      VS.mostrarAlerta(aviso, "");
    } catch (e) {
      VS.mostrarAlerta(aviso, e.message, "warning");
      return;
    }
    if (corrida.status !== chave) {
      chave = corrida.status;
      desenhar(corrida);
    } else {
      const campo = painel.querySelector("[data-campo=posicao]");
      if (campo) campo.textContent = posicaoTexto(corrida);
    }
    if (corrida.status === "finalizada" || corrida.status === "cancelada") parar();
  }

  parar = VS.repetir(atualizar);
})();
