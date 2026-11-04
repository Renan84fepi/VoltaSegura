"use strict";
// Registro do service worker e botão "Instalar app" (RNF01).
(() => {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register(document.body.dataset.sw).catch((erro) => console.warn("Service worker:", erro));
    });
  }

  // Botão "Instalar app": some quando já está rodando como app instalado.
  // Chrome/Edge oferecem a instalação pelo evento beforeinstallprompt; nos outros
  // navegadores (e quando o Chrome ainda não ofereceu) o botão mostra como instalar.
  const botao = document.getElementById("btn-instalar");
  const ajuda = document.getElementById("ajuda-instalar");
  const instalado = () =>
    window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  let pedidoInstalacao = null;

  function instrucoes() {
    const ua = navigator.userAgent;
    // Em HTTP comum (ex.: IP da rede) o navegador não instala o app de verdade nem
    // libera o GPS, mas ainda cria um atalho na tela inicial.
    if (!window.isSecureContext) {
      const atalho = /iPhone|iPad|iPod/.test(ua)
        ? "No Safari, toque em Compartilhar → “Adicionar à Tela de Início”."
        : "Abra o menu ⋮ do navegador e toque em “Adicionar à tela inicial”.";
      return `${atalho} Em ${location.host} (HTTP comum) isso cria um atalho, não o app completo: ` +
        "o GPS e o modo offline só funcionam em endereço seguro (HTTPS). Veja docs/como-rodar.md.";
    }
    if (/iPhone|iPad|iPod/.test(ua)) return "No Safari, toque em Compartilhar e depois em “Adicionar à Tela de Início”.";
    if (/Android/.test(ua)) return "Abra o menu ⋮ do navegador e toque em “Instalar app” ou “Adicionar à tela inicial”.";
    if (/Firefox/.test(ua)) return "O Firefox para computador não instala apps. Use o Chrome ou o Edge.";
    if (/Safari/.test(ua) && !/Chrome|Edg/.test(ua)) return "No Safari do Mac, use Arquivo → “Adicionar ao Dock”.";
    return "Clique no ícone de instalar na barra de endereço (à direita) ou no menu ⋮ → “Transmitir, salvar e compartilhar” → “Instalar página como app”. Se não aparecer, o app pode já estar instalado.";
  }

  if (botao && !instalado()) botao.hidden = false;
  window.addEventListener("beforeinstallprompt", (evento) => {
    evento.preventDefault();
    pedidoInstalacao = evento;
  });
  botao?.addEventListener("click", async () => {
    if (pedidoInstalacao) {
      pedidoInstalacao.prompt();
      await pedidoInstalacao.userChoice;
      pedidoInstalacao = null;
      return;
    }
    if (ajuda) {
      ajuda.textContent = instrucoes();
      ajuda.hidden = !ajuda.hidden;
    }
  });
  window.addEventListener("appinstalled", () => {
    if (botao) botao.hidden = true;
    if (ajuda) ajuda.hidden = true;
  });

  // Privacidade: o resumo da corrida guardado no aparelho (RNF02) some ao sair.
  const esquecer = () => {
    try {
      localStorage.removeItem("vs:corrida");
    } catch {
      // armazenamento indisponível: nada a apagar
    }
  };
  if (document.body.dataset.autenticado !== "1") esquecer();
  document.getElementById("form-sair")?.addEventListener("submit", esquecer);
})();
