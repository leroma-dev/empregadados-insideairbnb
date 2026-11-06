# Empregados InsideAirbnb

Projeto de dados sobre os anúncios de Airbnb no Rio de Janeiro, a partir do
dataset público [Inside Airbnb](https://insideairbnb.com/). O projeto
transforma os arquivos brutos em indicadores e mostra esses indicadores num
painel para anfitriões e investidores.

## O que o projeto faz

1. **Ingestão:** lê os quatro arquivos brutos e grava no banco, sem alterar nada.
2. **Staging:** converte os tipos, remove linhas repetidas e valida os valores.
3. **Marts:** responde nove perguntas de negócio, uma tabela por pergunta.
4. **Publicação:** exporta os marts para arquivos Parquet, para o painel publicado.
5. **Dashboard:** duas páginas, Anfitrião e Investidor, com uma explicação em
   cada gráfico.

## Para quem é

- **Anfitriões:** para decidir preço e comparar o próprio imóvel com o bairro.
- **Investidores:** para decidir em que bairro entrar e qual receita esperar.

## Onde começar

- Quer rodar o projeto? Veja [Instalação e comandos](instalacao.md).
- Quer entender cada etapa? Veja [Pipeline](pipeline.md).
- Quer saber o que cada número significa? Veja [Indicadores](indicadores.md).
