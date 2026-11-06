# Indicadores

Cada indicador responde a uma pergunta. Os números abaixo são os da última
execução do pipeline.

## Ocupação

A ocupação é a parte dos dias do calendário em que o imóvel aparece como
indisponível. Ela conta reservas **e** bloqueios feitos pelo anfitrião, porque
o dado não separa os dois.

## Receita potencial

É o preço do anúncio multiplicado pelos dias ocupados no mês. O calendário não
traz o preço de cada dia, então o cálculo usa o preço do anúncio para o ano
inteiro. Por isso é uma **estimativa**.

## Sazonalidade

Mostra em quais meses do ano há mais avaliações. Como os anos não têm o mesmo
número de meses com dados, cada mês é a média dos anos em que existe. O ano de
2026 está incompleto e entra só nos meses já ocorridos.

## Correlação

O indicador de comodidades usa a correlação de Pearson (r), de -1 a 1. Um r perto
de 0 quer dizer que não há relação linear. Relação não é prova de causa.

## Perguntas respondidas

1. Qual o preço médio e mediano da diária por bairro?
2. Qual a taxa de ocupação estimada por bairro?
3. Qual a receita potencial mensal por anúncio?
4. Qual a fatia de anfitriões com mais de um imóvel? (23,9% dos anfitriões; 57,6%
   dos imóveis)
5. Como evolui o número de avaliações por mês, e há sazonalidade?
6. Quanto custa a mais um imóvel inteiro em relação a um quarto privado?
7. Superhosts têm notas e ocupação maiores?
8. Há relação entre o número de comodidades e o preço ou a nota?
