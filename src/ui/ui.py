"""
Explorador do banco pelo navegador: abre data/insideairbnb.duckdb na
interface web da extensão ui do DuckDB.

STATUS: somente especificação. Código ainda não escrito.

Uso previsto: uv run python src/ui/ui.py

REGRAS

U1. O que faz: abre data/insideairbnb.duckdb, executa INSTALL ui; LOAD ui;
    e CALL start_ui(), que sobe o servidor em http://localhost:4213 e abre
    o navegador.

U2. Fica de pé até Ctrl+C: a extensão serve enquanto a conexão estiver viva.
    O script mantém o processo rodando, imprime a URL e a instrução
    "Ctrl+C para encerrar". No Ctrl+C fecha a conexão e sai sem traceback.
    Por quê: o arquivo .duckdb aceita um único processo escrevendo. Com este
    script de pé, a ingestão falha com "Could not set lock on file". Saber
    exatamente como desligar o servidor faz parte da ferramenta.

U3. Não cria banco: se data/insideairbnb.duckdb não existir, diz que é
    preciso rodar a ingestão antes e encerra com sys.exit(1).
    NÃO usa conectar() de pipeline/db.py, que cria o arquivo quando ele falta.
    Por quê: um banco vazio aberto no navegador parece ingestão quebrada.

U4. Separação: este script não importa pipeline/ingestao.py, e a ingestão
    não importa este script. A ingestão não sobe servidor, não abre navegador
    e não depende da extensão ui para rodar.
    Por quê: cada etapa roda sem a outra.

U5. Saída na tela: stdout reconfigurado para utf-8, pelo mesmo motivo da
    ingestão (Prompt de Comando do Windows).

CRITÉRIOS DE ACEITE

- uv run python src/ui/ui.py abre o navegador em localhost:4213, com o schema
  raw e as quatro tabelas (anuncios, calendario, avaliacoes, bairros).
- Ctrl+C devolve o terminal sem traceback, e logo depois a ingestão roda sem
  erro de lock.
- Renomear data/insideairbnb.duckdb faz o script parar com a mensagem, sem
  criar arquivo novo.
"""
