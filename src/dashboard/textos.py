"""Textos de titulo e explicacao de cada grafico do dashboard.

STATUS: redacao feita pelo construtor e APROVADA pelo autor antes da
publicacao (Task 8 do plano).

Regras: ate tres frases, linguagem simples para anfitriao e investidor, com as
ressalvas da spec (ocupacao inclui bloqueios do anfitriao; receita e uma
estimativa com o preco do anuncio no ano; 2026 e um ano incompleto).
"""

from typing import NamedTuple


class Texto(NamedTuple):
    titulo: str
    explicacao: str


TEXTOS: dict[str, Texto] = {
    "preco_bairro": Texto(
        "Preço médio por bairro",
        "Mostra quanto custa, em média, a diária em cada bairro. "
        "Bairros mais caros costumam ficar perto dos pontos turísticos e da praia.",
    ),
    "ocupacao_bairro": Texto(
        "Ocupação por bairro",
        "Mostra a parte do ano em que os imóveis ficam sem vaga para reserva. "
        "Atenção: esse número inclui os bloqueios do anfitrião, então não são só estadias reais. "
        "Por isso ele pode estar acima da ocupação de verdade.",
    ),
    "receita_mensal": Texto(
        "Receita mensal estimada",
        "É uma estimativa, calculada com o preço do anúncio no ano e não com o valor realmente cobrado. "
        "Use como ordem de grandeza, não como ganho garantido. "
        "O ano de 2026 está incompleto e por isso aparece com menos meses.",
    ),
    "reviews_mensal": Texto(
        "Avaliações por mês",
        "Conta quantas avaliações os hóspedes deixam a cada mês, o que indica o movimento de estadias. "
        "Nem todo hóspede avalia, então o número real de estadias é maior. "
        "O ano de 2026 está incompleto.",
    ),
    "sazonalidade": Texto(
        "Sazonalidade ao longo do ano",
        "Mostra em quais meses a procura sobe e desce. "
        "Ajuda a planejar preço e reformas fora da alta temporada. "
        "O ano de 2026 está incompleto e pode distorcer a comparação.",
    ),
    "inteiro_vs_privado": Texto(
        "Imóvel inteiro ou quarto privado",
        "Compara o preço mediano e o preço médio de quem aluga o imóvel inteiro com o de quem aluga só um quarto. "
        "Mostra também a diferença percentual entre os dois tipos.",
    ),
    "superhost": Texto(
        "Superhost ou anfitrião comum",
        "Compara os anúncios de Superhosts com os dos demais anfitriões. "
        "Mostra se o selo vem acompanhado de melhor resultado, mas não prova que o selo é a causa.",
    ),
    "multi_host": Texto(
        "Anfitriões com vários imóveis",
        "Mostra a parte dos anfitriões que têm vários imóveis (23,9%) e a parte dos anúncios que eles concentram (57,6%). "
        "Ou seja, poucos anfitriões seguram mais da metade dos anúncios.",
    ),
    "amenities": Texto(
        "Comodidades e resultado",
        "Mostra a correlação (r) entre o número de comodidades do anúncio e o preço, e entre o número de comodidades e a nota. "
        "Um r perto de 0 quer dizer que não há relação; quanto mais longe de 0, mais os dois andam juntos. "
        "Relação não é prova de causa: ter mais comodidades não garante, por si só, preço ou nota maiores.",
    ),
}
