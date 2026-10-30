# Histórico dos prompts

| Versão | Data | O que mudou | Por quê |
|---|---|---|---|
| v1 | 2026-10-20 | Primeira versão: etapas 0 e 1 (setup e contas) | Dividir o projeto em etapas para evitar código frágil de um prompt único |
| v2 | 2026-10-22 | Etapas 2 e 3 (veículos, documentos e CNH, bicicleta, repasse e aprovação pelo admin). Acrescenta restrições de privacidade (arquivos sem URL pública, sem `MEDIA_URL`), validação de upload, normalização de campos com máscara e uso das APIs atuais do Django | Documentos são dados sensíveis (RNF07); campos mascarados estouravam o `max_length`; e o agente tendia a usar APIs descontinuadas da versão instalada |
| v3 | 2026-10-28 | Etapas 4 a 7 (disponibilidade, solicitação, despacho e ciclo da corrida). Exige um módulo único de regras, mapa de transições, `select_for_update` + índices únicos parciais, regras de cancelamento explícitas e teste de aceite simultâneo com threads | As regras RN01–RN05 são avaliadas nos casos-limite; concorrência e sequência de status não ficam garantidas só com validação na view |

## Erros do agente em regras de negócio
Formato: o erro, a regra violada (RN##), como foi detectado e como o prompt foi corrigido.

| Data | Prompt | Erro | Regra | Detecção | Correção |
|---|---|---|---|---|---|
| 2026-10-28 | v3 | No teste do preço, o valor esperado usou `quantize()` sem modo de arredondamento (padrão do Python: arredondamento bancário, `ROUND_HALF_EVEN`), enquanto o sistema usa `ROUND_HALF_UP`. Com R$ 5,00 + R$ 2,50 × 5,29 km = R$ 18,225, o teste esperava R$ 18,22 e o sistema calculava R$ 18,23 | RN06 / RN08 | Teste automatizado falhou (`test_preco_segue_a_formula_configuravel`) | Prompt v3 passa a exigir arredondamento explícito `ROUND_HALF_UP` para centavos em todo cálculo de dinheiro, inclusive nos testes |
