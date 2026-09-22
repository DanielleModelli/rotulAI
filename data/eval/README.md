# Conjunto de avaliação

`gold_v1.jsonl`, uma linha por rótulo. 40 rótulos, 3 categorias reguladas por
rótulo, 120 decisões binárias.

## Proveniência

Rótulos de produtos comercializados no Brasil, coletados do Open Food Facts em
22/09/2026 pelo subdomínio `br.openfoodfacts.org`. Cada linha guarda a URL do
produto, então qualquer decisão é rastreável até a fonte.

Foram coletados 989 produtos brutos, dos quais 244 traziam a declaração
obrigatória de alérgenos embutida no texto e 235 sobreviveram aos filtros de
qualidade. Os 40 finais saíram desse conjunto por cotas de estrato.

## O gabarito vem do fabricante, não de nós

A verdade de referência é a **declaração obrigatória do próprio fabricante**
("ALÉRGICOS: CONTÉM ..."), exigida pela RDC 26/2015. É critério externo aos
autores do sistema, e essa é a principal mitigação contra a circularidade de
avaliar o próprio trabalho.

O campo `ingredients_text`, que é o que entra no sistema, **não contém a
declaração**: ela é separada e guardada em `declared_allergens_text`. A ausência
de vazamento é verificada automaticamente na montagem.

Leitura das cláusulas, por precedência:

| Cláusula | Interpretação |
|---|---|
| `NÃO CONTÉM X` | negativo explícito |
| `PODE CONTER X` | traços, contaminação cruzada, **não** conta como presente |
| `CONTÉM X` | presente |

Categoria não mencionada na declaração é tratada como ausente, já que a
declaração é obrigatória quando o alérgeno está presente.

## Estratos

Cada par (rótulo, categoria) recebe um estrato. É ele que permite reportar o
desempenho separadamente, em vez de um F1 agregado que não responde à pergunta
de pesquisa.

| Estrato | Significado | Decisões |
|---|---|---:|
| `explicito` | o nome comum aparece na lista de ingredientes | 35 |
| `oculto_na_base` | só há nome técnico, e ele **está** na base curada | 14 |
| `oculto_fora_base` | só há nome técnico, e ele **não está** na base curada | 14 |
| `distrator` | alérgeno ausente, mas há termo lexicalmente próximo | 26 |
| `ausente` | alérgeno ausente, sem termo próximo | 31 |

Total: 63 positivos e 57 negativos.

**`oculto_fora_base` é o estrato decisivo.** Ele mede quanto do desempenho vem
da cobertura da curadoria e quanto vem de generalização semântica. Se o recall
nele for próximo de zero, o sistema é um dicionário com busca por similaridade,
e isso precisa ser reportado.

**`distrator`** contém casos como `maltodextrina` e `amido modificado` em
produtos que declaram "NÃO CONTÉM GLÚTEN", `gordura vegetal` e `manteiga de
cacau` sem leite, `lecitina` sem soja. É o que separa detecção semântica de
busca por substring.

## O gabarito confia no fabricante

Regra assimétrica, deliberada:

- **Declarou "CONTÉM X" → presente.** Não cabe a nós desmentir o fabricante, que
  conhece o processo produtivo. Mesmo quando nenhum ingrediente correspondente
  aparece na lista (declaração por linha compartilhada), o gabarito é positivo.
- **Não declarou e o sistema aponta → divergência conservadora.** Conta como
  falso positivo nas métricas, mas é reportada à parte, porque é candidata a não
  conformidade e do ponto de vista de segurança alimentar é o erro barato.

A assimetria segue o risco: para quem tem alergia, falso negativo é risco à
saúde e falso positivo é inconveniência.

**Consequência a declarar.** 10 rótulos têm `sem_evidencia_no_texto` não vazio:
o fabricante declarou, mas não há termo correspondente na lista de ingredientes.
Nesses casos o sistema **não tem como acertar**, porque a informação não está na
sua entrada. Isso deprime o recall do estrato `oculto_fora_base`, e é limitação
da entrada, não da recuperação. As métricas são reportadas **com e sem** esses
casos, para que a diferença fique visível.

## Limitações conhecidas

- O conjunto não é amostra aleatória do mercado: é estratificado para ser
  informativo, e as proporções entre estratos não representam prevalência real.
- A cobertura do Open Food Facts é colaborativa e enviesada para produtos de
  marcas maiores e de consumo urbano.
- Traços ("pode conter") são tratados como ausência, porque o sistema analisa a
  lista de ingredientes e não o processo produtivo. É uma escolha declarada.

## Reprodução

```
python scripts/eval/coleta_off.py off_bruto.jsonl   # coleta (depende da rede e do OFF)
python scripts/eval/montar_dataset.py               # estratifica e seleciona
```

A seleção usa semente fixa (`20260922`). A coleta depende da disponibilidade do
Open Food Facts, que devolveu 503 em parte das consultas na data da coleta.
