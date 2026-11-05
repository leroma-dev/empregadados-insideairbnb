"""
Ingestão raw: os quatro arquivos de data/raw/ entram no DuckDB, schema raw,
exatamente como chegaram.

STATUS: somente especificação. Código ainda não escrito.

MAPA ARQUIVO -> TABELA

    listings.csv.gz      -> raw.anuncios
    calendar.csv.gz      -> raw.calendario
    reviews.csv.gz       -> raw.avaliacoes
    neighbourhoods.csv   -> raw.bairros

Os nomes em português são o vocabulário que o desenvolvedor digita de memória
em JOINs.

REGRAS

1. Antes de abrir o banco, verifica se os quatro arquivos existem em data/raw/.
   Faltando qualquer um: lista os que faltam, mostra a pasta onde procurou e
   encerra com sys.exit(1). Não ingere nada parcialmente.
   Por quê: ingerir três tabelas em silêncio gera um dashboard errado que
   parece certo.

2. Proibições (a regra central desta etapa):
   nenhuma conversão de tipo, nenhuma linha descartada ou deduplicada, nenhum
   nome de coluna alterado, nenhum valor corrigido, preenchido ou normalizado.
   Data continua texto; nulo continua nulo.
   Por quê: a fronteira entre "o dado que chegou" e "o dado que eu decidi"
   precisa existir em um lugar só. Esse lugar é a passagem de raw para staging
   (etapa 2). Se a correção acontecer aqui, a fronteira some.

3. Reexecução: a tabela é recriada com CREATE OR REPLACE, nunca acrescentada.
   Rodar dez vezes dá o mesmo resultado que rodar uma.
   Por quê: permite errar e rodar de novo sem medo.

4. Leitura: encoding="utf-8" declarado, nunca adivinhado. Os .csv.gz são lidos
   direto, sem descompactar. Campo vazio vira nulo, não string vazia.
   Por quê: a leitura não pode depender de detecção automática, que erra sem
   aviso.

5. Tipagem: toda coluna entra como texto (dtype=str), com inferência
   desligada.
   Por quê: a inferência lê CEP com zero à esquerda como número, e o zero
   desaparece sem aviso. A conversão acontece na etapa 2, como decisão
   registrada.

6. Valores que o pandas trata como nulo por padrão ("NA", "null", "N/A",
   "NaN") devem continuar texto. Usar keep_default_na=False e na_values=[""].
   Por quê: sem isso, o pandas converte esses textos em nulo sem aviso, o que
   é uma correção de valor escondida dentro da ingestão.

7. Escrita atômica: toda a ingestão roda em uma única transação. Se falhar
   no meio, o banco fica no estado anterior, não parcial.
   Por quê: um banco com algumas tabelas novas e outras antigas seria um
   estado que ninguém decidiu ter.

8. Saída na tela: uma linha por tabela, com nome qualificado e contagem de
   linhas vinda do banco (não do DataFrame), milhar separado por ponto. Uma
   linha final com o total. stdout reconfigurado para utf-8.
   Por quê: a saída é o único instrumento de conferência nesta etapa. O
   usuário roda no Prompt de Comando do Windows, onde acento sai embaralhado
   sem essa configuração.

9. O script termina sozinho e devolve o terminal. Nenhum processo fica de pé.

CRITÉRIOS DE ACEITE

- A execução imprime uma linha por tabela (quatro) e o total de registros.
- Duas execuções seguidas imprimem exatamente a mesma coisa.
- SELECT * FROM raw.anuncios devolve todas as colunas como VARCHAR.
- Remover um dos quatro arquivos faz o script parar antes de gravar qualquer tabela.
- O processo termina sozinho.

SEPARAÇÃO

Este módulo não sobe servidor, não abre navegador e não depende da extensão
ui do DuckDB. Não importa src/ui/ui.py, e src/ui/ui.py não importa este módulo.
"""
