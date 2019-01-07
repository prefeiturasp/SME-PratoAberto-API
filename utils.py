import collections


def sort_cardapio_por_refeicao(refeicoes_desord):
    ordens_refeicao = ['Desjejum', 'Colação', 'Almoço', 'Lanche', 'Refeição da Tarde',
                       'Lanche - Permanência de 4 ou 8 horas',
                       'Lanche - Permanência de 5 ou 6 horas', 'Lanche - Permanência de 5 ou 6 horas', 'Refeição',
                       'Merenda Seca',
                       'Merenda Inicial', 'Refeição - Professor', 'Pro Jovem (filhos)', 'Almoço - Professor',
                       'Jantar - Professor',
                       'Refeição']
    ordenado = collections.OrderedDict()
    for ordem_refeicao in ordens_refeicao:
        for _ in refeicoes_desord:
            if not (ordem_refeicao in ordenado) and ordem_refeicao in refeicoes_desord:
                ordenado[ordem_refeicao] = refeicoes_desord[ordem_refeicao]
    return ordenado


def remove_refeicao_duplicada_sme_conv(refeicoes):
    retval = []
    for refeicao in refeicoes:
        if refeicao['idade'] != 'Toda Idade':  # remove "toda idade" e deixa somente "todas as idades"
            retval.append(refeicao)
    return retval


if __name__ == '__main__':
    import json

    cardapio = {
        "Almoço": ["ARROZ", "FEIJ\u00c3O CARIOCA", "FONTE DE PROTE\u00cdNA (*); BATATA DOCE COZIDA", "MA\u00c7\u00c3",
                   "(*) Fonte de prote\u00edna -\u00a0\u00a0Oferecer semanalmente carne bovina; frango; ovo e peixe (atentar-se a presen\u00e7a de espinhas); quinzenalmente carne su\u00edna (corte magro) e mensalmente PTS."],
        "Colação": ["MA\u00c7\u00c3"],
        "Desjejum": ["LEITE MATERNO OU F\u00d3RMULA INFANTIL (2\u00ba SEMESTRE)", "BISCOITO"], "Refeição da Tarde": [
            "SOPA: MACARR\u00c3O; FEIJ\u00c3O CARIOCA; FONTE DE PROTE\u00cdNA (*); BATATA; CENOURA; CHUCHU", "ABACATE",
            "(*) Fonte de prote\u00edna \u2013 Carne bovina e frango variando na semana. Variar tamb\u00e9m diariamente a fonte de de prote\u00edna do almo\u00e7o e da refei\u00e7\u00e3o da tarde"],
        "Lanche": ["LEITE MATERNO OU F\u00d3RMULA INFANTIL (2\u00ba SEMESTRE)"]}

    cardapio_sorted = sort_cardapio_por_refeicao(cardapio)
    print(cardapio_sorted['Desjejum'])

    print(json.dumps(cardapio, indent=4))
    print('________')
    print(json.dumps(cardapio_sorted, indent=4))
