import collections
import datetime


def sort_cardapio_por_refeicao(refeicoes_desord):
    ordens_refeicao = ['Desjejum', 'Colação', 'Almoço', 'Lanche', 'Refeição da Tarde',
                       'Lanche - Permanência de 4 ou 8 horas',
                       'Lanche - Permanência de 5 ou 6 horas', 'Lanche - Permanência de 5 ou 6 horas',
                       'Lanche Período Integral', 'Refeição',
                       'Merenda Seca', 'Merenda Especial Seca',
                       'Merenda Inicial', 'Refeição - Professor', 'Pro Jovem (filhos)', 'Almoço - Professor',
                       'Jantar - Professor',
                       'Refeição', 'Sem Refeição', 'Horário estendido', 'Lanche passeio']
    ordenado = collections.OrderedDict()
    for ordem_refeicao in ordens_refeicao:
        for _ in refeicoes_desord:
            if not (ordem_refeicao in ordenado) and ordem_refeicao in refeicoes_desord:
                ordenado[ordem_refeicao] = refeicoes_desord[ordem_refeicao]
    return ordenado


def remove_refeicao_duplicada_sme_conv(refeicoes):
    retval = []
    refeicoes = sorted(refeicoes, key=lambda r: len(r['cardapio']), reverse=True)
    len_todas_as_idades = (list(refeicoes[0]['cardapio'])).__len__()
    todas_as_idades_contem_refeicao = 'Refeição' in list(refeicoes[0]['cardapio'])
    for refeicao in refeicoes:
        if len_todas_as_idades == 1 or not todas_as_idades_contem_refeicao or (len_todas_as_idades == 2 and refeicao['idade'] != 'Toda Idade'):
            retval.append(refeicao)
    return retval


def extract_digits(word):
    digits_extracted = ''.join([p for p in word if p in '0123456789']) or None
    if digits_extracted:
        return int(digits_extracted)
    return digits_extracted


def extract_chars(word):
    return ''.join([p for p in word if p not in '0123456789'])


def translate_date_month(month):
    month_dict = {
        1: 'Janeiro',
        2: 'Fevereiro',
        3: 'Março',
        4: 'Abril',
        5: 'Maio',
        6: 'Junho',
        7: 'Julho',
        8: 'Agosto',
        9: 'Setembro',
        10: 'Outubro',
        11: 'Novembro',
        12: 'Dezembro',
    }
    return month_dict[month]


def translate_date_week(day):
    week_day = {
        0: 'Segunda-feira',
        1: 'Terça-feira',
        2: 'Quarta-feira',
        3: 'Quinta-feira',
        4: 'Sexta-feira',
        5: 'Sábado',
        6: 'Domingo',
    }

    return week_day[day]


def datetime_range(start=None, end=None):
    dates = []
    if isinstance(start, str):
        start = datetime.datetime.strptime(start, '%Y%m%d').date()
    if isinstance(end, str):
        end = datetime.datetime.strptime(end, '%Y%m%d').date()
    span = end - start
    for i in range(span.days + 1):
        dates.append((start + datetime.timedelta(days=i)).strftime('%Y%m%d'))
    return dates
