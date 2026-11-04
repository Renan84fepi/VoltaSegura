# Prompt v4.1 — Ajustes do Marco 4 (identidade visual, instalação pelo celular e PWA atrás do túnel)

> Pré-requisito: prompt v4 concluído e validado (pagamento, avaliação, histórico, PWA e offline com `pytest` passando).

## Contexto
VoltaSegura: PWA em Django em que clientes pedem um motorista para conduzir o carro do cliente; o motorista chega com uma mini bicicleta elétrica dobrável. Ainda estamos no **Marco 4 — Pagamento, avaliação e PWA**. As funcionalidades estão prontas. Nos testes no celular apareceram três problemas: a interface parecia um protótipo do Bootstrap e não um app (RNF03); o manifesto não carregava pelo ngrok gratuito; e, aberto pelo IP da rede (HTTP), o botão "Instalar app" só dizia para usar HTTPS. Esta etapa corrige isso **sem mexer em regras de negócio**.

## Tarefa desta etapa
1. **Tema visual (RNF03):** criar `pwa/static/pwa/tema.css`, carregado depois do Bootstrap, com as cores, os raios e as sombras em variáveis CSS (`--vs-*`). As variáveis do Bootstrap (`--bs-*`) passam a apontar para elas. Os estilos que estavam no `<style>` do `base.html` vão para esse arquivo.
2. **Navegação de app (RNF03):** barra superior fixa com a marca, os links do perfil, "Instalar app" e "Sair". Para cliente e motorista, abas fixas na parte de baixo da tela, com ícone e texto e a aba atual destacada (`request.resolver_match.view_name`). Respeitar a área segura do iPhone (`viewport-fit=cover`, `env(safe-area-inset-*)`).
3. **Login e cadastro:** cabeçalho com o logo e uma frase curta, e o formulário dentro de um cartão.
4. **Página offline (RNF02):** usar o tema novo, mas manter um estilo mínimo próprio no `<style>`, porque o Bootstrap ou o tema podem não estar no cache.
5. **Manifesto (RNF01):** `theme_color` e `background_color` iguais ao fundo do tema, também na `<meta name="theme-color">` do `base.html` e da página offline. O `<link rel="manifest">` usa `crossorigin="use-credentials"`.
6. **Cache do service worker:** incluir `tema.css` nos arquivos essenciais e aumentar `VERSAO_CACHE`, para os aparelhos trocarem o cache antigo.
7. **Instalação por HTTP:** sem contexto seguro (`window.isSecureContext` falso), o botão "Instalar app" explica como criar um atalho em "Adicionar à tela inicial" (Safari no iPhone, menu ⋮ no Android). Também avisa que, nesse caso, GPS e modo offline só funcionam em HTTPS.

## Restrições
- **Só aparência:** não mudar IDs, classes nem atributos `data-*` usados pelo JavaScript (`corridas/*.js`, `pwa/*.js`), nem views, URLs, modelos ou regras.
- Sem bibliotecas novas: ícones em SVG embutido no template, sem pacote de ícones. A única dependência externa nova é a fonte Inter, do Google Fonts, com fonte do sistema como alternativa.
- Contraste legível e botões grandes, com pelo menos 44 px de altura de toque.
- A API, o admin e os documentos continuam fora do cache (regra do v4).
- Interface em pt-BR (RNF14).

## Critérios de aceite
- Todas as telas de cliente e motorista funcionam como antes: pedir, acompanhar, aceitar, código, pagar, avaliar, ganhos e histórico.
- As abas inferiores aparecem só para cliente e motorista logados (não para o admin nem na tela de login), e o conteúdo não fica escondido atrás delas.
- Pelo túnel ngrok, o DevTools → Application → Manifest carrega sem erro, e o Chrome do celular oferece a instalação.
- Aberto por `http://<IP>:<porta>`, "Instalar app" mostra as instruções de atalho com o aviso sobre HTTPS.
- Depois de atualizar, o service worker novo instala e o `tema.css` funciona offline.
- `pytest` passa; listar arquivos alterados e roteiro de teste manual (computador e celular).

## Formato da resposta
Plano curto → código por arquivo → roteiro de teste manual.
