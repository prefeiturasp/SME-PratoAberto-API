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


def extract_digits(word):
    digits_extracted = ''.join([p for p in word if p in '0123456789']) or None
    if digits_extracted:
        return int(digits_extracted)
    return digits_extracted


def extract_chars(word):
    return ''.join([p for p in word if p not in '0123456789'])
