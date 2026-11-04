"use strict";
// Página offline (RNF02): mostra o último estado salvo da corrida e volta sozinha.
(() => {
  const $ = (id) => document.getElementById(id);
  let salvo = null;
  try {
    salvo = JSON.parse(localStorage.getItem("vs:corrida") || "null");
  } catch {
    salvo = null;
  }

  if (salvo) {
    $("corrida").hidden = false;
    $("status").textContent = `Corrida #${salvo.id}: ${salvo.status_texto}`;
    $("origem").textContent = salvo.origem;
    $("destino").textContent = salvo.destino;
    $("salvo-em").textContent = `(às ${new Date(salvo.salvo_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })})`;
    if (salvo.codigo) {
      $("bloco-codigo").hidden = false;
      $("codigo").textContent = salvo.codigo;
    }
    if (salvo.contato) {
      $("bloco-contato").hidden = false;
      $("contato-nome").textContent = salvo.contato.nome;
      $("contato-tel").textContent = salvo.contato.telefone;
      $("contato-tel").href = `tel:${salvo.contato.telefone}`;
    }
  }

  // Ao voltar a conexão, recarrega a própria página que o usuário tentou abrir.
  const recarregar = () => location.reload();
  $("tentar").addEventListener("click", recarregar);
  window.addEventListener("online", recarregar);
})();
