# Dashboard Streamlit: design

Status: APROVADA. As três perguntas abertas seguem como premissas do plano (ver `docs/spec/11_plano_dashboard.md`).

Escrito para: quem vai planejar e construir o dashboard, e quem vai aprovar o
escopo.

## Intenção

Anfitriões e investidores usam o dashboard para tomar decisões sobre imóveis
do Inside Airbnb. Cada indicador vem com uma explicação curta, visível logo
abaixo do título do gráfico, para que quem lê saiba o que o número significa
antes de decidir.

## Objetivos

- Duas páginas, uma para anfitriões e uma para investidores.
- Cada indicador tem título, gráfico e uma explicação de 1 a 3 frases.
- Os números vêm dos nove marts da etapa 3 e não são recalculados no app.
- O app roda localmente com um comando do uv, e também fica publicado na
  internet.

## Não-objetivos

- Não há cadastro, login nem área privada.
- Não há escrita no banco: o app só lê.
- Não há previsão de preço nem recomendação automática de bairro.
- Não se refaz nenhuma conta dos marts no app.

## Antiobjetivos (o que faria isto falhar mesmo funcionando)

- Um número sem explicação, ou com explicação técnica que um anfitrião não
  entende.
- Um dado publicado que não bate com o banco local.
- O app publicado mostrar um mart desatualizado sem aviso.

## Restrições

- Python 3.13 e uv, como no resto do projeto.
- Streamlit é a biblioteca de apresentação (definido em
  `docs/spec/01_spec_projeto.md`). Entra como dependência nova do
  `pyproject.toml` na etapa de plano, e só após esta aprovação.
- O arquivo `data/insideairbnb.duckdb` tem cerca de 1,2 GB e não pode ser
  publicado.
- O `.gitignore` ignora `data/staging/` e o `.duckdb`. A exportação vai para
  `data/publicacao/`, que não é ignorada, para que os Parquet entrem no git.

## Abordagens consideradas

**A. Só local, lendo o banco direto.** Simples e sem duplicação, mas não há
como publicar.

**B. Publicar exportando os marts para Parquet, sem leitura direta.** O app
publicado funciona, mas o desenvolvimento local também passaria a depender
dos arquivos exportados.

**C. Escolhida: híbrida.** Localmente, o app lê o banco direto em modo
somente leitura. Para publicar, um passo separado exporta os nove marts para
Parquet, e o app publicado lê esses arquivos. A exportação usa o próprio
DuckDB (`COPY ... TO ... (FORMAT parquet)`), sem biblioteca extra.

Motivo da escolha: a leitura direta evita duplicação no uso diário, e a
exportação só existe para a publicação.

## Decisões tomadas

1. Duas páginas no Streamlit, uma por público. Página "Anfitrião": preço por
   bairro, imóvel inteiro versus quarto privado, ocupação por bairro,
   amenities. Página "Investidor": receita mensal, ocupação por bairro,
   sazonalidade das reviews, multi-host, superhosts.
2. Cada gráfico tem explicação curta, em texto fixo, guardada num módulo
   Python separado do código de gráficos.
3. O app lê de `mart.*` (local) ou de arquivos Parquet (publicado). A camada
   de leitura é a única que sabe qual dos dois está em uso.
4. Exportação em `data/publicacao/`, uma tabela por arquivo, com o mesmo nome
   do mart (`preco_bairro.parquet`, etc.). Pasta nova, minha escolha: não
   fica em `data/mart/`, para não misturar o que é fonte com o que é cópia.
5. Comando local: `scripts/comandos_uv.sh dashboard`, no padrão dos outros.
6. Publicação em Streamlit Community Cloud, a partir do repositório do GitHub.
   Os Parquet de `data/publicacao/` são versionados no git (são pequenos).
   Minha escolha: essa é a hospedagem mais simples para Streamlit. Se você
   preferir outra, a parte de exportação não muda.

## O que fica para o construtor

- Organização de pastas do código em `src/`, dentro das regras do projeto.
- Ordem e tamanho dos gráficos dentro de cada página.
- Como o app detecta que está publicado ou local (variável de ambiente ou
  presença dos arquivos).
- Testes: unitários para a camada de leitura e para os textos, e checagem
  manual do layout.

## Chamadas feitas no desenho (minhas, para conferir)

- Atualização: a exportação roda à mão, depois de `pipeline.marts`. Junto
  com os Parquet, grava um arquivo `data/publicacao/atualizacao.json` com a
  data de geração. O app mostra essa data no rodapé: "dados gerados em
  <data>".
- Receita mensal: a página mostra a soma dos anúncios por mês, não a média
  por anúncio. A conta é a soma do que já está em `mart.receita_mensal_anuncio`.
- Preço e ocupação por bairro: gráfico de barras horizontais com os 15 bairros
  de maior valor, e uma tabela completa abaixo com todos os 156 bairros. Não
  há mapa, porque os marts não têm coordenadas.
- Amenities: o gráfico mostra a correlação com preço e com nota, com a
  frase de leitura. Não há distribuição porque a mart tem uma linha.
- Multi-host, superhost e imóvel inteiro versus quarto privado: barras
  simples ou rosca, com o número ao lado.
- Investidor: usa `sazonalidade_reviews` para o padrão do ano. `reviews_mensal`
  fica na página, como série histórica com o mesmo tema.
- Explicações: cada uma fica no módulo de textos. Incluem as ressalvas de
  ocupação (inclui bloqueios do anfitrião), de receita (estimativa com o preço
  do anúncio para o ano) e de 2026 (período incompleto).
- Dependências: o Streamlit entra num grupo de dependências separado do
  pipeline, para que a publicação instale só o necessário.

## Respostas do autor (perguntas abertas)

1. Repositório no GitHub: público.
2. Filtros: não haverá na primeira versão.
3. Textos das explicações: o construtor redige; o autor aprova antes da publicação.

## Critérios de aceite (rascunho)

- `scripts/comandos_uv.sh dashboard` abre o app local, lendo do banco.
- O comando de exportação gera os nove Parquet em `data/publicacao/`, e os
  totais batem com os de `mart.*` (MA2 a MA9 da etapa 3).
- Cada gráfico tem uma explicação visível, com até 3 frases.
- A página publicada lê só os Parquet, sem tocar no `.duckdb`.
