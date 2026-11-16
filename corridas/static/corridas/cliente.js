"use strict";
// Telas do cliente: solicitar (C2/C3), acompanhar (C4) e, ao final, pagar e avaliar (C5).

// ------------------------------------------------------------ solicitar
(() => {
  const raiz = document.getElementById("pedido");
  if (!raiz) return;
  const $ = (id) => document.getElementById(id);
  const origem = $("origem");
  const destino = $("destino");
  let posicaoAparelho = null; // RF09: coordenadas do GPS, se o cliente usar
  let estimativa = null; // resposta da API, com coordenadas já resolvidas
  let referencia = null; // posição do aparelho, mesmo após editar a coleta: orienta a busca do endereço

  // Se a localização já foi liberada antes, pega a posição sem perguntar nada.
  navigator.permissions?.query({ name: "geolocation" }).then((estado) => {
    if (estado.state !== "granted") return;
    VS.posicaoAtual({ precisaoAlvo: 1000 }).then((p) => { referencia = referencia || p; }, () => {});
  }, () => {});

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
      referencia = posicaoAparelho;
      origem.value = "Minha localização atual";
      const metros = Math.round(posicaoAparelho.precisao);
      if (metros > 200) {
        // Sem GPS (ex.: computador), o navegador estima pela rede e pode errar por quilômetros.
        aviso.className = "form-text text-warning";
        aviso.textContent = `Localização aproximada (±${metros} m). Se estiver errada, digite o endereço de coleta.`;
      } else {
        aviso.className = "form-text text-success";
        aviso.textContent = `Localização obtida (±${metros} m).`;
      }
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
      referencia_latitude: referencia?.latitude ?? null,
      referencia_longitude: referencia?.longitude ?? null,
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
      // O que a busca encontrou: se caiu em outra cidade, o cliente percebe antes de pedir.
      const encontrados = [
        estimativa.origem_encontrada && `Coleta: ${estimativa.origem_encontrada}`,
        estimativa.destino_encontrado && `Destino: ${estimativa.destino_encontrado}`,
      ].filter(Boolean);
      $("conf-encontrados").hidden = !encontrados.length;
      $("conf-encontrados").textContent = encontrados.join(" • ");
      const perto = estimativa.motoristas_proximos;
      $("conf-motoristas").className = `alert py-2 small ${perto ? "alert-success" : "alert-warning"}`;
      $("conf-motoristas").textContent = perto
        ? `${perto} motorista(s) disponível(is) perto da coleta.`
        : `Nenhum motorista disponível a até ${VS.distancia(estimativa.raio_oferta_km)} da coleta agora. ` +
          "Confira o endereço de coleta; se pedir, a busca continua até alguém ficar disponível.";
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

  function buscaTexto(perto) {
    return perto
      ? `Procurando um motorista próximo… (${perto} disponível(is) perto da coleta)`
      : "Nenhum motorista disponível perto da coleta no momento. Continuamos procurando…";
  }

  function posicaoTexto(corrida) {
    const p = corrida.posicao_motorista;
    if (!p) return "Aguardando a localização do motorista…";
    const alvo = p.alvo === "coleta" ? "do local de coleta" : "do destino";
    const quando = p.atualizada_em ? ` (atualizado às ${VS.hora(p.atualizada_em)})` : "";
    return `Motorista a ${VS.distancia(p.distancia_km)} ${alvo}${quando}`;
  }

  // RF21: pagamento simulado, depois da finalização.
  function pagamentoHtml(c) {
    const p = c.pagamento;
    if (!p) return "";
    const recibo = `<a href="${VS.esc(raiz.dataset.urlRecibo)}">Ver recibo</a>`;
    if (p.status === "aprovado") {
      return `<div class="alert alert-success"><strong>Pagamento aprovado.</strong>
        ${VS.dinheiro(p.valor_total)} • ${VS.esc(p.forma)} (simulado) • ${recibo}</div>`;
    }
    if (p.status === "estornado") {
      return `<div class="alert alert-secondary"><strong>Pagamento estornado.</strong> ${recibo}</div>`;
    }
    if (!p.pode_pagar) return "";
    return `<div class="card mb-3 border-warning"><div class="card-body">
      <h2 class="h5">Pagamento</h2>
      ${p.status === "recusado" ? `<div class="alert alert-danger py-2">Pagamento recusado. Tente novamente.</div>` : ""}
      <p class="mb-2">Total: <strong class="fs-4">${VS.dinheiro(p.valor_total)}</strong> • ${VS.esc(p.forma)}</p>
      <button id="btn-pagar" class="btn btn-success btn-lg w-100 mb-2">Pagar com ${VS.esc(p.forma)}</button>
      ${raiz.dataset.simulador ? `<button id="btn-recusar" class="btn btn-outline-warning btn-sm w-100">🧪 Simular pagamento recusado</button>` : ""}
      <div class="form-text">Pagamento simulado: nenhum valor é cobrado de verdade.</div>
    </div></div>`;
  }

  // RF23 + RN10: uma avaliação, só depois de finalizada.
  function avaliacaoHtml(c) {
    if (c.avaliacao) {
      return `<div class="card mb-3"><div class="card-body">
        <div class="small text-muted">Sua avaliação</div>
        <div class="fs-4 text-warning">${VS.estrelas(c.avaliacao.nota)}</div>
        ${c.avaliacao.comentario ? `<div class="small">${VS.esc(c.avaliacao.comentario)}</div>` : ""}
      </div></div>`;
    }
    if (!c.pode_avaliar) return "";
    const opcoes = [1, 2, 3, 4, 5].map((n) => `
      <input type="radio" class="btn-check" name="nota" id="nota-${n}" value="${n}">
      <label class="btn btn-outline-warning btn-lg flex-fill" for="nota-${n}">${n}★</label>`).join("");
    return `<form id="form-avaliacao" class="card mb-3"><div class="card-body">
      <h2 class="h5">Como foi o motorista?</h2>
      <div class="d-flex gap-1 mb-2" role="group" aria-label="Nota de 1 a 5">${opcoes}</div>
      <label class="form-label small" for="comentario">Comentário (opcional)</label>
      <textarea id="comentario" class="form-control mb-2" maxlength="500" rows="2"></textarea>
      <div id="erro-avaliacao" hidden></div>
      <button class="btn btn-primary btn-lg w-100" type="submit">Enviar avaliação</button>
    </div></form>`;
  }

  function desenhar(c) {
    const m = c.motorista;
    const final = c.status === "finalizada" || c.status === "cancelada";
    let html = "";
    if (c.status === "cancelada") {
      html += `<div class="alert alert-secondary"><strong>Corrida cancelada.</strong>
        ${c.motivo_cancelamento ? `<br>Motivo: ${VS.esc(c.motivo_cancelamento)}` : ""}</div>`;
    } else if (c.status === "finalizada") {
      html += `<div class="alert alert-light border"><strong>Corrida finalizada!</strong>
        Você chegou ao destino.</div>`;
      html += pagamentoHtml(c) + avaliacaoHtml(c);
    } else {
      html += `<div class="card mb-3"><div class="card-body">${VS.etapasHtml(c.status)}</div></div>`;
    }
    if (c.status === "solicitada") {
      const perto = c.motoristas_proximos;
      html += `<div class="alert ${perto ? "alert-info" : "alert-warning"} d-flex align-items-center gap-2">
        <span class="spinner-border spinner-border-sm"></span>
        <span data-campo="busca">${buscaTexto(perto)}</span></div>`;
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
        <div class="fw-bold">${VS.esc(m.nome)}
          <span class="fw-normal small text-muted">${VS.notaTexto(m.nota)}</span></div>
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
    if (final && !c.pagamento?.pode_pagar) {
      html += `<a class="btn btn-primary btn-lg w-100" href="${VS.esc(raiz.dataset.urlNova)}">Nova corrida</a>`;
    }
    painel.innerHTML = html;
    document.getElementById("btn-cancelar")?.addEventListener("click", cancelar);
    document.getElementById("btn-pagar")?.addEventListener("click", () => pagar("aprovado"));
    document.getElementById("btn-recusar")?.addEventListener("click", () => pagar("recusado"));
    document.getElementById("form-avaliacao")?.addEventListener("submit", avaliar);
  }

  async function pagar(resultado) {
    painel.querySelectorAll("#btn-pagar, #btn-recusar").forEach((b) => (b.disabled = true));
    try {
      desenhar(await VS.api(raiz.dataset.urlPagar, { metodo: "POST", dados: { resultado } }));
      VS.mostrarAlerta(aviso, "");
    } catch (e) {
      VS.mostrarAlerta(aviso, e.message);
      painel.querySelectorAll("#btn-pagar, #btn-recusar").forEach((b) => (b.disabled = false));
    }
  }

  async function avaliar(evento) {
    evento.preventDefault();
    const erro = document.getElementById("erro-avaliacao");
    const nota = painel.querySelector("input[name=nota]:checked");
    if (!nota) return VS.mostrarAlerta(erro, "Escolha uma nota de 1 a 5.");
    const botao = evento.target.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
      desenhar(await VS.api(raiz.dataset.urlAvaliar, {
        metodo: "POST",
        dados: { nota: Number(nota.value), comentario: document.getElementById("comentario").value },
      }));
    } catch (e) {
      VS.mostrarAlerta(erro, e.message);
      botao.disabled = false;
    }
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
      VS.guardarCorrida(corrida); // RNF02: a página offline mostra este último estado
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
      const busca = painel.querySelector("[data-campo=busca]");
      if (busca) {
        busca.textContent = buscaTexto(corrida.motoristas_proximos);
        busca.parentElement.classList.toggle("alert-info", !!corrida.motoristas_proximos);
        busca.parentElement.classList.toggle("alert-warning", !corrida.motoristas_proximos);
      }
    }
    if (corrida.status === "finalizada" || corrida.status === "cancelada") parar();
  }

  parar = VS.repetir(atualizar);
})();
