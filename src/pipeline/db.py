"""
Acesso ao banco DuckDB do projeto: data/insideairbnb.duckdb.

STATUS: somente especificação. Código ainda não escrito.

REGRAS

1. conectar() abre data/insideairbnb.duckdb. O caminho é calculado a partir
   da localização deste arquivo, nunca da pasta corrente.
   Por quê: se o caminho dependesse da pasta de onde o script roda, rodar de
   outra pasta criaria um banco novo lá, e a ingestão ficaria em um arquivo
   que ninguém procura.

2. conectar() cria o arquivo e o schema raw se faltarem.
   Por quê: a ingestão precisa poder rodar do zero, sem passo manual.
   Atenção: o explorador (ui.py) NÃO usa esta função, justamente para não
   abrir um banco vazio que pareça ingestão quebrada.

3. Importar este módulo não abre banco nem cria arquivo.
   Por quê: importar não pode ter efeito colateral. Testes e ferramentas
   importam o módulo sem intenção de gravar nada.

4. gravar(nome_qualificado, df) faz CREATE OR REPLACE TABLE e devolve a
   contagem de linhas consultada no banco, não len(df).
   Por quê: a contagem mostrada ao usuário precisa ser a do que de fato ficou
   gravado. CREATE OR REPLACE faz rodar duas vezes dar o mesmo resultado, sem
   acumular linhas.

CRITÉRIOS DE ACEITE

- Importar pipeline.db não abre banco nem cria arquivo.
- conectar() chamado de outra pasta cria data/insideairbnb.duckdb dentro do
  projeto, não na pasta corrente.
- gravar() com DataFrame de 3 linhas devolve 3; rodar de novo continua devolvendo 3.
"""
