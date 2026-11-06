# Pipeline

O pipeline tem quatro etapas. Cada uma lê só da etapa anterior e grava na sua.
A fronteira entre elas é deliberada: o que chegou (`raw`) fica separado do
que foi decidido (`staging`) e do que responde a uma pergunta (`mart`).

## 1. Ingestão (`raw`)

Lê `listings`, `calendar`, `reviews` e `neighbourhoods` e grava em `raw.*`.

- Tudo entra como texto. Não há conversão, descarte, deduplicação nem correção.
- Motivo: a fronteira entre o dado recebido e o dado decidido precisa existir
  em um lugar só, que é a passagem para `staging`.
- Se algum arquivo faltar, a ingestão para antes de gravar qualquer tabela.

## 2. Staging (`staging`)

Converte os tipos e valida os valores.

- Valor que não converte para o tipo alvo interrompe a execução, com a tabela,
  a coluna e um exemplo. Nunca vira nulo em silêncio.
- Linha inteira repetida sai, e a quantidade é contada.
- Chave repetida com conteúdo diferente interrompe a execução.
- Preço vira `DECIMAL(10,2)`, sem arredondamento: um valor com mais de duas
  casas decimais é recusado.
- Datas sem hora viram `DATE`.

## 3. Marts (`mart`)

Cada arquivo de `data/mart/` cria uma tabela. Os arquivos seguem o padrão
`XX_descricao.sql`, numerados a partir de 01.

- Cada arquivo tem uma única instrução `CREATE OR REPLACE TABLE`.
- As nove tabelas são criadas numa única transação. Se uma falhar, nenhuma é
  alterada.
- O Python não contém SQL de mart.

## 4. Publicação (`data/publicacao`)

Exporta os nove marts para arquivos Parquet e grava `atualizacao.json` com a
data de geração e a quantidade de linhas de cada tabela. Esses arquivos são o
que o painel publicado lê.
