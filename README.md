# Maceió, urna a urna

Mapa eleitoral de Maceió no 1º turno de 2026 (Presidente), local de votação por local de votação.
Levantamento por Vinícius Dias (@euvinidiass). Fontes: TSE (votação por seção e eleitorado por local de votação 2026), IBGE (bairros 2022, via geobr).

## Arquivos

- `index.html`: o mapa, pronto para publicar (página estática).
- `fonte/process.py`: cruza a votação por seção com o cadastro de locais de votação e gera `data.json`.
- `fonte/template.html`: o modelo da página; `geo.json` (bairros e municípios vizinhos) e `data.json` são inseridos nele para gerar o `index.html`.
