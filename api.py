# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

import math
import time
from bson import json_util, ObjectId
from dateutil.parser import parse
from flask import Flask, request, render_template, send_file
from flask_restplus import Api, Resource
from pymongo import MongoClient
from xhtml2pdf import pisa
from dotenv import load_dotenv
from flask_cors import CORS

import utils
from utils import (sort_cardapio_por_refeicao,
                   extract_digits,
                   extract_chars,
                   remove_refeicao_duplicada_sme_conv,
                   datetime_range, limpar_cardapios,
                   ORDEM_REFEICAO)

load_dotenv()

sentry_url = os.environ.get('SENTRY_URL')
if sentry_url:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_environment = os.environ.get('SENTRY_ENVIRONMENT')

    sentry_sdk.init(
        dsn=sentry_url,
        environment=sentry_environment,
        integrations=[FlaskIntegration()]
    )

app = Flask(__name__)
CORS(app)
api = Api(app, default='API do Prato Aberto', default_label='endpoints para se comunicar com a API do Prato Aberto')
API_KEY = os.environ.get('API_KEY')
API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))

client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']

with open('de_para.json', 'r') as f:
    conf = json.load(f)
    refeicoes = conf['refeicoes']
    idades = conf['idades']
    idades_reversed = {v: k for k, v in conf['idades'].items()}


@app.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0
    

@api.route('/escolas')
@api.response(200, 'lista de escolas')
class ListaEscolas(Resource):
    def get(self):
        """Retorna uma lista de escolas ativas"""
        query = {'status': 'ativo'}
        fields = {'_id': True, 'nome': True}
        try:
            limit = int(request.args.get('limit', 5))
            # busca por nome
            nome = request.args['nome']
            query['nome'] = {'$regex': nome.replace(' ', '.*'), '$options': 'i'}
            cursor = db.escolas.find(query, fields).limit(limit)
        except KeyError:
            fields.update({k: True for k in ['endereco', 'bairro', 'lat', 'lon']})
            cursor = db.escolas.find(query, fields)

        response = app.response_class(
            response=json_util.dumps(cursor),
            status=200,
            mimetype='application/json'
        )
        return response


@api.route('/escola/<int:id_escola>')
@api.doc(params={'id_escola': 'um código EOL de uma escola'})
@api.response(200, 'Dados da escola')
@api.response(404, 'Escola inexistente')
class DetalheEscola(Resource):
    def get(self, id_escola):
        """Retorna os dados relacionados à uma escola"""
        raw = request.args.get('raw', False)
        query = {'_id': id_escola, 'status': 'ativo'}
        fields = {'_id': False, 'status': False}
        escola = db.escolas.find_one(query, fields)
        editais = db.escolas_editais.find({'escola': int(id_escola)})
        if escola:
            escola['editais'] = editais
            if not raw:
                if 'idades' in escola:
                    escola['idades'] = [idades.get(x, x) for x in escola['idades']]
                if 'refeicoes' in escola:
                    escola['refeicoes'] = sorted(
                        [refeicoes.get(x, x) for x in escola['refeicoes']],
                        key=lambda r: ORDEM_REFEICAO.index(r) if r in ORDEM_REFEICAO else len(ORDEM_REFEICAO)
                    )
            response = app.response_class(
                response=json_util.dumps(escola),
                status=200,
                mimetype='application/json'
            )
        else:
            response = app.response_class(
                response=json_util.dumps({'erro': 'Escola inexistente'}),
                status=404,
                mimetype='application/json'
            )
        return response


@api.route('/escola/<int:id_escola>/cardapios/<data>')
@api.route('/escola/<int:id_escola>/cardapios/')
@api.doc(params={'id_escola': 'um código EOL de uma escola', 'data': 'data de um cardápio'})
class CardapioEscola(Resource):
    def get(self, id_escola, data=None):
        """retorna os cardápios de uma escola em um período"""
        escola = db.escolas.find_one({'_id': id_escola}, {'_id': False})
        if escola:
            query = {
                'status': 'PUBLICADO',
                'agrupamento': str(escola['agrupamento']),
                'tipo_atendimento': escola['tipo_atendimento'],
                'tipo_unidade': escola['tipo_unidade']
            }

            if request.args.get('idade'):
                query['idade'] = idades_reversed.get(request.args['idade'])

            if data:
                query['data'] = str(data)
            else:
                data = {}
                if request.args.get('data_inicial'):
                    data.update({'$gte': request.args['data_inicial']})
                if request.args.get('data_final'):
                    data.update({'$lte': request.args['data_final']})
                if data:
                    query['data'] = data

            fields = {
                '_id': False,
                'status': False,
                'cardapio_original': False
            }

            _cardapios = []
            cardapios = db.cardapios.find(query, fields).sort([('data', -1)]).limit(15)
            for c in cardapios:
                c['idade'] = idades[c['idade']]
                c['cardapio'] = sort_cardapio_por_refeicao(c['cardapio'])
                c['cardapio'] = {refeicoes[k]: v for k, v in c['cardapio'].items()}
                _cardapios.append(c)
            cardapios = _cardapios

            response = app.response_class(
                response=json_util.dumps(cardapios),
                status=200,
                mimetype='application/json'
            )
        else:
            response = app.response_class(
                response=json_util.dumps({'erro': 'Escola inexistente'}),
                status=404,
                mimetype='application/json'
            )
        return response


@api.route('/ajuste-datas-cardapios/')
class AjusteDatasCardapios(Resource):
    def get(self):
        hoje = datetime.now()
        json_cardapios = db.cardapios.find({'data': 'Data'})
        for cardapio in json_cardapios:
            id = cardapio['_id']
            cardapio['data'] = datetime.strftime(hoje, '%Y%m%d')
            db.cardapios.update_one({"_id": ObjectId(id)}, {"$set": cardapio})
        return app.response_class(
            response=json_util.dumps({'message': 'Datas alteradas para hoje'}),
            status=200,
            mimetype='application/json'
        )


@api.route('/editor/unidade-especial/<id>')
class UnidadeEspecial(Resource):
    def get(self, id):
        json_ue = db.unidades_especiais.find_one({'_id': ObjectId(id)})
        return app.response_class(
            response=json_util.dumps(json_ue),
            status=200,
            mimetype='application/json'
        )


@api.route('/editor/cardapios-unidade-especial/')
class CardapioUnidadeEspecial(Resource):
    def get(self):
        unit_id = request.args.get('unidade')
        begin = request.args.get('inicio')
        end = request.args.get('fim')

        query = {
            '_id': ObjectId(unit_id),
            'data_inicio': begin,
            'data_fim': end
        }

        special_unit = db.unidades_especiais.find_one(query)
        if special_unit:
            query_menu = {"tipo_unidade": special_unit['nome'],
                          "data": {"$gte": begin, "$lte": end},
                          "status": 'PUBLICADO'}

            menu_ue = db.cardapios.find(query_menu)
        else:
            menu_ue = {}

        return app.response_class(
            response=json_util.dumps(menu_ue),
            status=200,
            mimetype='application/json'
        )

    def post(self):
        pass


@api.route('/cardapios/<data>')
@api.route('/cardapios/')
@api.doc(params={'data': 'data de um cardápio'})
class Cardapios(Resource):
    def get(self, data=None):
        """retorna os cardápios relacionados a um período"""
        cardapio_ordenado = find_menu_json(request, data)

        response = app.response_class(
            response=json_util.dumps(cardapio_ordenado),
            status=200,
            mimetype='application/json'
        )
        return response


def _filter_category(descriptions):
    category_dict = {}

    for age, day in descriptions.items():
        for day, menu in day.items():
            category_dict[age] = menu.keys()
    return category_dict


def _reorganizes_date(menu_dict):
    date_dict = {}

    for age, menu in menu_dict.items():
        date_dict[age] = []
        for key in menu:
            if key['data'] not in date_dict[age]:
                date_dict[age].append(key['data'])

    return date_dict


def _reorganizes_category(menu_dict, menu_type_by_school=None):
    category_dict = {}
    for age, menu in menu_dict.items():
        all_categories = set()
        for day in menu:
            all_categories.update(day['cardapio'].keys())
        categories = list(all_categories)
        if menu_type_by_school:
            category_dict[age] = _order_categories_by_school(categories,
                                                             menu_type_by_school)
        else:
            category_dict[age] = _change_order_categories_list(categories)

    return category_dict


def _order_categories_by_school(categories, menu_type_by_school):
    ordered_categories = []
    for cat in menu_type_by_school:
        if cat in categories:
            ordered_categories.append(cat)
    for cat in categories:
        if cat not in ordered_categories:
            ordered_categories.append(cat)
    return ordered_categories


def _change_order_categories_list(categories):
    if 'Colação' in categories:
        colacao_index = categories.index('Colação')
        value = categories.pop(colacao_index)
        categories.insert(1, value)

    return categories


def _reorganizes_menu_week(menu_dict):
    age_dict = {}
    for age, values in menu_dict.items():
        age_dict[age] = []
        values = sorted(values, key=lambda v: v['data'])
        for val in values:
            age_dict[age].append(val)

    return age_dict


def _get_school_by_name(school_name):
    new_list_category = []
    school = db.escolas.find({"nome": school_name})
    for category in school[0]['refeicoes']:
        if refeicoes[category]:
            new_list_category.append(refeicoes[category])

    return new_list_category, school[0]['idades'], school[0]['refeicoes']


def _get_school_id(school_name):
    school = db.escolas.find({"nome": school_name})
    try:
        return str(school[0]['_id'])
    except (ValueError, IndexError):
        return None


def _get_special_unit_by_school_id_and_date(id_school, start):
    ue = db.unidades_especiais.find_one({"data_inicio": start, "escolas": {'$all': [id_school]}})
    try:
        return ue
    except ValueError:
        return None


def filter_by_menu_school(categories, menu_type_by_school):
    new_dict_categories = {}
    for key, values in categories.items():
        new_dict_categories[key] = []
        for category in values:
            if category in menu_type_by_school:
                new_dict_categories[key].append(category)

    return new_dict_categories


@api.route('/cardapio-pdf/<data>')
@api.route('/cardapio-pdf')
@api.doc(params={'data': 'data de um cardápio'})
class ReportPdf(Resource):

    def _get_current_date(self, inicio, fim):
        if inicio.month == fim.month:
            month = '{} a {} de {} de {}'.format(inicio.day, fim.day, utils.translate_date_month(inicio.month),
                                                 inicio.year)
        else:
            month = '{} de {} a {} de {} de {}'.format(inicio.day, utils.translate_date_month(inicio.month), fim.day,
                                                       utils.translate_date_month(fim.month), inicio.year)

        return month

    def get(self, data=None):
        """retorna um PDF para impressão de um cardápio em um período"""
        response_menu = adjust_ages(find_menu_json(request, data, is_pdf=True))
        response = {}

        menu_type_by_school, _, _ = _get_school_by_name(request.args.get('nome'))
        school_id = _get_school_id(request.args.get('nome'))

        inicio = datetime.strptime(request.args.get('data_inicial'), '%Y%m%d')
        fim = datetime.strptime(request.args.get('data_final'), '%Y%m%d')

        refeicoes_vigencias = _get_vigencias_ativas_no_periodo(
            school_id,
            request.args.get('data_inicial'),
            request.args.get('data_final')
        )

        menu_types_efetivos = menu_type_by_school + [
            r for r in refeicoes_vigencias if r not in menu_type_by_school
        ]

        formated_data = _reorganizes_data_menu(response_menu)
        date_organizes = _reorganizes_date(formated_data)
        catergory_ordered = _reorganizes_category(formated_data, menu_types_efetivos)

        menu_organizes = _reorganizes_menu_week(formated_data)

        filtered_category_ordered = filter_by_menu_school(catergory_ordered, menu_types_efetivos)

        current_date = self._get_current_date(inicio, fim)
        response['school_name'] = request.args.get('nome')
        response['response'] = response_menu
        response['week_menu'] = current_date

        cpath = os.path.realpath(os.path.dirname(__file__)) + '/static/'

        wipe_unused(cpath, 5)
        publication_date = parse(response_menu[0]['data_publicacao']).strftime('%d/%m/%Y %H:%M:%S')

        html = render_template('cardapio-pdf.html', resp=response, descriptions=formated_data, dates=date_organizes,
                               categories=filtered_category_ordered, menus=menu_organizes, publication=publication_date)
        # return Response(html, mimetype="text/html")

        pdf = _create_pdf(html)
        pdf_name = pdf.split('/')[-1]

        return send_file(pdf, mimetype=pdf_name)


@app.template_filter('fmt_day_month')
def format_day_month(value):
    if value is not None:
        # current_date = datetime.strptime(value, '%Y%m%d')
        return datetime.strftime(value, '%d/%m')
    return value


@app.template_filter('fmt_week_day')
def format_day_month(value):
    if value is not None:
        # current_date = datetime.strptime(value, '%Y%m%d')
        return utils.translate_date_week(value.weekday())
    return value


# Factory PDF
def _create_pdf(pdf_data):
    today = datetime.now()

    cdir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(cdir, 'static')
    if not os.path.exists(path):
        os.mkdir(path)
    name = 'cardapio_mensal_{}.pdf'.format(datetime.strftime(today, '%d_%m_%Y_%H_%M_%S'))
    filename = os.path.join(path, name)

    resultFile = open(filename, "w+b")

    # convert HTML to PDF
    pisa.CreatePDF(pdf_data, dest=resultFile)  # file handle to recieve result

    # close output file
    resultFile.close()

    return filename


def adjust_ages(menu_dict):
    if next((True for item in menu_dict if item['idade'] == 'Toda Idade'), False) and \
            next((True for item in menu_dict if item['idade'] == 'Todas as idades'), False):
        menu_dict_ordered = sorted(menu_dict, key=lambda kv: (kv['data'], kv['idade']))
        cardapio = None
        for value in menu_dict_ordered:
            if value['idade'] == 'Toda Idade':
                cardapio = dict(value['cardapio'])
            elif value['idade'] == 'Todas as idades' and cardapio:
                value['cardapio'].update(cardapio)
        just_all_ages = []
        for value in menu_dict_ordered:
            if value['idade'] == 'Todas as idades':
                just_all_ages.append(value)
        return just_all_ages
    return menu_dict


def _reorganizes_data_menu(menu_dict):
    age_list = []
    age_dict = {}

    [age_list.append(value['idade']) for value in menu_dict if value['idade'] not in age_list]

    for age in age_list:
        for data in menu_dict:
            if data['idade'] == age:
                age_dict[age] = []
        for data in menu_dict:
            if data['idade'] in age_dict:
                age_dict[age] = []
    return _sepate_for_age(age_dict, menu_dict)


def _sepate_for_age(key_dict, data_dict):
    groupment = False
    if len(data_dict) and data_dict[0]['agrupamento'] == 'UE':
        groupment = True

    for value in data_dict:
        if value['idade'] in key_dict.keys():
            key_dict[value['idade']].append({'data': _converter_to_date(value['data']), 'cardapio': value['cardapio'],
                                             'publicacao': _set_datetime(value['data_publicacao'])})

    if groupment:
        return key_dict

    return _separate_menu_by_category(key_dict)


def _separate_menu_by_category(data):
    orphan_list = {}
    new_list = {}
    just_one = False
    """ Loop to separate dicts """
    for key, values in data.items():
        new_list[key] = []
        orphan_list[key] = []
        for value in values:
            if len(value['cardapio']) == 1:
                new_list[key].append(value)
                just_one = True
            elif len(value['cardapio']) > 1:
                new_list[key].append(value)
            else:
                orphan_list[key].append(value)
    if just_one:
        return new_list
    return _mixer_list_menu(new_list, orphan_list)


def _mixer_list_menu(new_list, orphan_list):
    if len(orphan_list) > 0:
        for key, value in new_list.items():
            cont = 0
            for v in value:
                for or_key, or_value in orphan_list.items():
                    if len(or_value) > 0:
                        for o_v in or_value:
                            if key == or_key and v['data'] == o_v['data']:
                                key_orphan = list(o_v['cardapio'].keys())[0]
                                value_orphan = list(o_v['cardapio'].values())[0]
                                new_list[key][cont]['cardapio'][key_orphan] = value_orphan
                cont = cont + 1
    return new_list


def _set_datetime(str_date):
    try:
        ndate = parse(str_date)
        return ndate.strftime('%d/%m/%Y - %H:%M:%S')
    except Exception as e:
        print(str(e))
        return str_date


def _converter_to_date(str_date):
    return datetime.strptime(str_date, '%Y%m%d')


def wipe_unused(basedir, limit):
    """
    Remove files in *basedir* not accessed within *limit* minutes

    :param basedir: directory to clean
    :param limit: minutes
    """
    if os.path.exists(basedir):
        atime_limit = time.time() - limit
        count = 0
        for filename in os.listdir(basedir):
            path = os.path.join(basedir, filename)
            if os.path.getatime(path) < atime_limit:
                os.remove(path)
                count += 1
        print("Removed {} files.".format(count))


def find_menu_json(request_data, dia, is_pdf=False):
    """ Return json's menu from a school """
    school_name = request_data.args.get('nome')

    if not dia:
        start = request_data.args.get('data_inicial')
        end = request_data.args.get('data_final')
    else:
        start = dia
        end = dia

    school_id = _get_school_id(school_name)
    if is_pdf:
        ue = _get_special_unit_by_school_id_and_date(school_id, start)
        if ue:
            end = ue['data_fim']

    query_unidade_especial = {
        'escolas': school_id,
        'data_inicio': {'$lte': start},
        'data_fim': {'$gte': end}
    }

    unidade_especial = db.unidades_especiais.find_one(query_unidade_especial)

    query = {
        'status': 'PUBLICADO'
    }

    if request_data.args.get('tipo_unidade'):
        query['tipo_unidade'] = request_data.args['tipo_unidade'] if not unidade_especial else unidade_especial['nome']
    if request_data.args.get('idade'):
        query['idade'] = idades_reversed.get(request_data.args['idade'])

    if dia:
        dias = [dia]
    else:
        dias = datetime_range(request_data.args.get('data_inicial'), request_data.args.get('data_final'))

    _cardapios = []
    for dia_ in dias:
        edital_corrente = db.escolas_editais.find_one(
            {
                'escola': int(school_id),
                '$or': [
                    {
                        '$and': [
                            {'data_inicio': {'$lte': str(dia_)}},
                            {'data_fim': None}
                        ]
                    },
                    {
                        '$and': [
                            {'data_inicio': {'$lte': str(dia_)}},
                            {'data_fim': {'$gte': str(dia_)}}
                        ]
                    }
                ]
            }
        )
        tipo_gestao_corrente = edital_corrente['tipo_atendimento'] if edital_corrente else 'TERCEIRIZADA'
        if request_data.args.get('tipo_atendimento'):
            query['tipo_atendimento'] = tipo_gestao_corrente if not unidade_especial else 'UE'
        edital_corrente_nome = edital_corrente['edital'] if edital_corrente else 'EDITAL 78/2016'
        query['agrupamento'] = edital_corrente_nome if not unidade_especial else 'UE'
        if request_data.args.get('tipo_unidade') == "PROJETO_CECI":
            query['tipo_unidade'] = request_data.args.get('tipo_unidade')
            query['tipo_atendimento'] = request_data.args.get('tipo_atendimento')
            query['agrupamento'] = request_data.args.get('agrupamento')
        query['data'] = dia_

        fields = {
            '_id': False,
            'status': False,
            'cardapio_original': False,
        }
        cardapios = db.cardapios.find(query, fields)
        for c in cardapios:
            _cardapios.append(c)

    cardapio_ordenado = []
    definicao_ordenacao = ['A - 0 A 1 MES', 'B - 1 A 3 MESES', 'C - 4 A 5 MESES', 'D - 0 A 5 MESES', 'D - 6 A 7 MESES',
                           'D - 6 MESES', 'D - 7 MESES', 'E - 7 A 11 MESES', 'E - 8 A 11 MESES', 'X - 1A -1A E 11MES',
                           'F - 1 A 3 ANOS', 'F - 2 A 3 ANOS', 'G - 4 A 6 ANOS', 'I - 2 A 6 ANOS', 'W - EMEI DA CEMEI',
                           'N - 6 A 7 MESES PARCIAL', 'O - 8 A 11 MESES PARCIAL', 'Y - 1A -1A E 11MES PARCIAL',
                           'P - 2 A 3 ANOS PARCIAL', 'Q - 4 A 6 ANOS PARCIAL', 'H - ADULTO', 'Z - UNIDADES SEM FAIXA',
                           'S - FILHOS PRO JOVEM', 'V - PROFESSOR', 'U - PROFESSOR JANTAR CEI',
                           'T - TURMAS DO INFANTIL']
    category_by_school = None
    school_ages = None
    refeicoes_raw = None

    if request_data.args.get('nome'):
        category_by_school, school_ages, refeicoes_raw = _get_school_by_name(request_data.args.get('nome'))

    for i in definicao_ordenacao:
        for c in _cardapios:
            if i == c['idade'] and i in school_ages:
                cardapio_ordenado.append(c)
                continue

    for c in cardapio_ordenado:
        try:
            refeicoes_copia = refeicoes_raw.copy()
            vigente, nao_vigente = _get_vigencias_by_school_id(school_id, c['data'])

            # Adiciona os vigentes que ainda não estão
            for r in vigente:
                if r not in refeicoes_copia:
                    refeicoes_copia.append(r)

            # Remove os não vigentes que ainda estão
            for r in nao_vigente:
                if r in refeicoes_copia:
                    refeicoes_copia.remove(r)

            category_by_school_pos_vigencias = []
            for category in refeicoes_copia:
                if refeicoes[category]:
                    category_by_school_pos_vigencias.append(refeicoes[category])

            c['idade'] = idades[c['idade']]
            c['cardapio'] = {refeicoes[k]: v for k, v in c['cardapio'].items()}
            if category_by_school_pos_vigencias:
                c['cardapio'] = {k: v for k, v in c['cardapio'].items() if k in category_by_school_pos_vigencias}

            if is_pdf:
                missing = set(category_by_school_pos_vigencias) - set(c['cardapio'].keys())
                removed = set(category_by_school) - set(category_by_school_pos_vigencias)
                diff = list(missing | removed)
                for refeicao_diff in diff:
                    c['cardapio'][refeicao_diff] = ['-']

        except KeyError as e:
            app.logger.debug('erro de chave: {} objeto {}'.format(str(e), c))

    cardapio_ordenado = limpar_cardapios(cardapio_ordenado)

    for c in cardapio_ordenado:
        c['cardapio'] = sort_cardapio_por_refeicao(c['cardapio'])

    if query['tipo_unidade'] == 'SME_CONVÊNIO' and len(cardapio_ordenado):
        cardapio_ordenado = remove_refeicao_duplicada_sme_conv(cardapio_ordenado)

    return cardapio_ordenado


def _get_vigencias_by_school_id(school_id, data_str):
    data_ref = datetime.strptime(data_str, "%Y%m%d")

    vigencias = db.vigencias_tipo_alimentacao.find({"escola_id": str(school_id)})
    resultado = {"vigente": [], "nao_vigente": []}

    for vigencia in vigencias:
        data_inicio = vigencia.get("data_inicio")
        data_fim = vigencia.get("data_fim")

        data_inicio = datetime.strptime(data_inicio, "%Y%m%d") if data_inicio else None
        data_fim = datetime.strptime(data_fim, "%Y%m%d") if data_fim is not None else None

        if (data_inicio is None or data_ref >= data_inicio) and (data_fim is None or data_ref <= data_fim):
            resultado["vigente"].extend(vigencia.get("refeicoes", []))
        else:
            resultado["nao_vigente"].extend(vigencia.get("refeicoes", []))

    return resultado["vigente"], resultado["nao_vigente"]


def _get_vigencias_ativas_no_periodo(school_id, data_inicial, data_final):
    data_inicio_ref = datetime.strptime(data_inicial, "%Y%m%d")
    data_fim_ref = datetime.strptime(data_final, "%Y%m%d")

    vigencias = db.vigencias_tipo_alimentacao.find({"escola_id": str(school_id)})
    refeicoes_ativas = set()

    for vigencia in vigencias:
        v_data_inicio = vigencia.get("data_inicio")
        v_data_fim = vigencia.get("data_fim")

        v_data_inicio = datetime.strptime(v_data_inicio, "%Y%m%d") if v_data_inicio else None
        v_data_fim = datetime.strptime(v_data_fim, "%Y%m%d") if v_data_fim is not None else None

        if v_data_inicio is None:
            v_data_inicio = data_inicio_ref
        if v_data_fim is None:
            v_data_fim = data_fim_ref

        if (v_data_fim >= data_inicio_ref) and (v_data_inicio <= data_fim_ref):
            for r in vigencia.get("refeicoes", []):
                refeicoes_ativas.add(refeicoes.get(r, r))

    return list(refeicoes_ativas)


@api.route('/editor/cardapios')
class CardapiosEditor(Resource):
    def get(self):
        db.cardapios.create_index([('data', -1)])
        """retorna os cardápios para o editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        query = {}
        if request.args.get('status'):
            query['status'] = {'$in': request.args.getlist('status')}
        else:
            query['status'] = 'PUBLICADO'
        if request.args.get('unidade_especial') and request.args.get('unidade_especial') != 'NENHUMA':
            query['tipo_unidade'] = request.args.get('unidade_especial')
            query['tipo_atendimento'] = 'UE'
            query['agrupamento'] = 'UE'
        else:
            if request.args.get('agrupamento') and request.args.get('agrupamento') != 'TODOS':
                query['agrupamento'] = request.args['agrupamento']
            if request.args.get('tipo_atendimento') and request.args.get('tipo_atendimento') != 'TODOS':
                query['tipo_atendimento'] = request.args['tipo_atendimento']
            if request.args.get('tipo_unidade') and request.args.get('tipo_unidade') != 'TODOS':
                query['tipo_unidade'] = request.args['tipo_unidade']
        if request.args.get('idade') and request.args.get('idade') != 'TODOS':
            query['idade'] = request.args['idade']
        data = {}
        if request.args.get('data_inicial'):
            data.update({'$gte': request.args['data_inicial']})
        if request.args.get('data_final'):
            data.update({'$lte': request.args['data_final']})
        if data:
            query['data'] = data

        limit = int(request.args.get('limit', 0))
        page = int(request.args.get('page', 0))
        cardapios = db.cardapios.find(query).sort([('data', -1)])
        if page and limit:
            cardapios = cardapios.skip(limit * (page - 1)).limit(limit)
        elif limit:
            cardapios = cardapios.limit(limit)

        response = app.response_class(
            response=json_util.dumps(cardapios),
            status=200,
            mimetype='application/json'
        )
        return response

    def post(self):
        """atualiza os cardápios pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        bulk = db.cardapios.initialize_ordered_bulk_op()
        for item in json_util.loads(request.data.decode("utf-8")):
            if '_id' in item:
                _id = item['_id']
                bulk.find({'_id': _id}).update({'$set': item})
            else:
                cardapio = db.cardapios.find_one({
                    'tipo_atendimento': item['tipo_atendimento'],
                    'agrupamento': item['agrupamento'],
                    'tipo_unidade': item['tipo_unidade'],
                    'idade': item['idade'],
                    'data': item['data']})
                if cardapio:
                    item['cardapio'].update(cardapio['cardapio'])
                    item['cardapio_original'].update(cardapio['cardapio_original'])
                    bulk.find({'_id': cardapio['_id']}).update({'$set': item})
                else:
                    bulk.insert(item)
        bulk.execute()
        return ('', 200)


@api.route('/editor/cardapios-unidades-especiais')
class CardapiosUnidadesEspeciaisEditor(Resource):
    def get(self):
        """retorna os cardápios de unidades especiais para o editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        query = {}
        query['status'] = {'$in': request.args.getlist('status')}
        query['tipo_atendimento'] = 'UE'
        query['agrupamento'] = 'UE'
        if request.args.get('unidade_especial') and request.args.get('unidade_especial') != 'NENHUMA':
            query['tipo_unidade'] = request.args.get('unidade_especial')
        if request.args.get('idade') and request.args.get('idade') != 'TODOS':
            query['idade'] = request.args['idade']
        data = {}
        if request.args.get('data_inicial'):
            data.update({'$gte': request.args['data_inicial']})
        if request.args.get('data_final'):
            data.update({'$lte': request.args['data_final']})
        if data:
            query['data'] = data

        limit = int(request.args.get('limit', 0))
        page = int(request.args.get('page', 0))
        cardapios = db.cardapios.find(query).sort([('data', -1)])
        if page and limit:
            cardapios = cardapios.skip(limit * (page - 1)).limit(limit)
        elif limit:
            cardapios = cardapios.limit(limit)

        response = app.response_class(
            response=json_util.dumps(cardapios),
            status=200,
            mimetype='application/json'
        )
        return response


@api.route('/v2/editor/escolas')
class EscolasEditor(Resource):
    def get(self):
        """retorna as escolas para o editor"""
        try:
            key = request.headers.get('key')
            if key and API_KEY and key != API_KEY:
                return '', 401
            query = {'status': 'ativo'}
            if request.args:
                nome_ou_eol = request.args.get('nome', None)
                if nome_ou_eol:
                    if any(char.isdigit() for char in nome_ou_eol):
                        eol = extract_digits(nome_ou_eol)
                        query['_id'] = eol
                    else:
                        nome = extract_chars(nome_ou_eol)
                        query['nome'] = {'$regex': nome.replace(' ', '.*'), '$options': 'i'}
                agrupamento = request.args.get('agrupamento', None)
                if agrupamento and agrupamento != 'TODOS':
                    query['agrupamento'] = agrupamento
                tipo_atendimento = request.args.get('tipo_atendimento', None)
                if tipo_atendimento and tipo_atendimento != 'TODOS':
                    query['tipo_atendimento'] = tipo_atendimento
                tipo_unidade = request.args.get('tipo_unidade', None)
                if tipo_unidade:
                    query['tipo_unidade'] = {'$regex': tipo_unidade.replace(' ', '.*'), '$options': 'i'}
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 100))
            total_documents = db.escolas.find(query).count()
            total_pages = math.ceil(total_documents / limit)
            if page > total_pages > 0:
                raise Exception('pagina nao existe')
            from_doc = (page * limit) - limit
            to_doc = page * limit if page * limit < total_documents else total_documents
            cursor = db.escolas.find(query).sort('_id', 1)[from_doc:to_doc]
        except Exception as exception:
            return app.response_class(
                json_util.dumps({'erro': str(exception)}),
                status=400,
                mimetype='application/json'
            )
        else:
            return app.response_class(
                json_util.dumps([cursor, {
                    'total_pages': total_pages,
                    'next': page + 1 if page < total_pages else None,
                    'previous': page - 1 if page > 1 else None
                }]),
                status=200,
                mimetype='application/json'
            )


@api.route('/editor/escola/<int:id_escola>')
@api.doc(params={'id_escola': 'um código EOL de uma escola'})
class EditarEscola(Resource):
    def post(self, id_escola):
        """atualiza dados de uma escola pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        app.logger.debug(request.json)
        try:
            payload = request.json
        except:
            return app.response_class(
                response=json_util.dumps({'erro': 'Dados POST não é um JSON válido'}),
                status=500,
                mimetype='application/json'
            )
        db.escolas_editais.delete_many({'escola': int(id_escola)})
        if 'edital_1' in payload:
            edital_1 = payload.pop('edital_1')
            db.escolas_editais.insert_one(edital_1)
        if 'edital_2' in payload:
            edital_2 = payload.pop('edital_2')
            db.escolas_editais.insert_one(edital_2)
        db.escolas.update_one(
            {'_id': id_escola},
            {'$set': payload},
            upsert=True)
        return ('', 200)

    def delete(self, id_escola):
        """exclui uma escola pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        try:
            db.escolas.delete_one(
                {'_id': id_escola})
        except:
            return ('', 400)
        return ('', 200)


@api.route('/editor/unidade_especial/<string:id_unidade_especial>')
@api.route('/editor/unidade_especial/')
@api.doc(params={'id_unidade_especial': 'id da unidade especial'})
class EditarUnidadeEspecial(Resource):
    def get(self, id_unidade_especial):
        """retorna dados de uma unidade especial pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        query = {'_id': id_unidade_especial, 'status': 'ativo'}
        fields = {'_id': False, 'status': False}
        special_unit = db.unidades_especiais.find_one(query, fields)
        if special_unit:
            response = app.response_class(
                response=json_util.dumps(special_unit),
                status=200,
                mimetype='application/json'
            )
        else:
            response = app.response_class(
                response=json_util.dumps({'erro': 'Unidade especial inexistente'}),
                status=404,
                mimetype='application/json'
            )
        return response

    def post(self, id_unidade_especial=None):
        """atualiza dados de uma unidade especial pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        app.logger.debug(request.json)
        try:
            payload = request.json
            if '_id' in payload:
                del payload['_id']
        except:
            return app.response_class(
                response=json_util.dumps({'erro': 'Dados POST não é um JSON válido'}),
                status=500,
                mimetype='application/json'
            )
        db.unidades_especiais.update_one(
            {'_id': ObjectId(id_unidade_especial)},
            {'$set': payload},
            upsert=True)
        return ('', 200)

    def delete(self, id_unidade_especial):
        """exclui uma escola pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        try:
            db.unidades_especiais.delete_one(
                {'_id': ObjectId(id_unidade_especial)})
        except:
            return ('', 400)
        return ('', 200)


@api.route('/editor/vigencia_tipo_alimentacao/<string:id_vigencia>')
@api.route('/editor/vigencia_tipo_alimentacao/')
@api.doc(params={'id_vigencia': 'id da vigencia'})
class EditarVigenciaTipoAlimentacao(Resource):
    def get(self, id_vigencia):
        """retorna dados de uma vigência tipo alimentação pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        query = {'_id': id_vigencia, 'status': 'ativo'}
        fields = {'_id': False, 'status': False}
        special_unit = db.vigencias_tipo_alimentacao.find_one(query, fields)
        if special_unit:
            response = app.response_class(
                response=json_util.dumps(special_unit),
                status=200,
                mimetype='application/json'
            )
        else:
            response = app.response_class(
                response=json_util.dumps({'erro': 'Vigência tipo alimentação inexistente'}),
                status=404,
                mimetype='application/json'
            )
        return response

    def post(self, id_vigencia=None):
        """atualiza dados de uma vigência tipo alimentação pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        app.logger.debug(request.json)
        try:
            payload = request.json
            if '_id' in payload:
                del payload['_id']
        except:
            return app.response_class(
                response=json_util.dumps({'erro': 'Dados POST não é um JSON válido'}),
                status=500,
                mimetype='application/json'
            )
        db.vigencias_tipo_alimentacao.update_one(
            {'_id': ObjectId(id_vigencia)},
            {'$set': payload},
            upsert=True)
        return ('', 200)

    def delete(self, id_vigencia):
        """exclui uma vigência tipo alimentação pelo editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        try:
            db.vigencias_tipo_alimentacao.delete_one(
                {'_id': ObjectId(id_vigencia)})
        except:
            return ('', 400)
        return ('', 200)


@api.route('/editor/unidades_especiais')
@api.response(200, 'lista de unidades especiais')
class ListaUnidadesEspeciais(Resource):
    def get(self):
        """Retorna uma lista de unidades especiais"""
        query = {}
        fields = {'_id': True, 'nome': True, 'data_criacao': True, 'data_inicio': True, 'data_fim': True,
                  'escolas': True}
        cursor = db.unidades_especiais.find(query, fields)
        response = app.response_class(
            response=json_util.dumps(cursor),
            status=200,
            mimetype='application/json'
        )
        return response


@api.route('/editor/remove-cardapio')
class RemoveCardapios(Resource):
    def post(self):
        """exclui um ou mais cardápio(s) pelo editor"""
        post = request.form['ids']
        ids_menu = json.loads(post)
        count = 0
        ''' Iteration and remove row'''
        for ids in ids_menu:
            count += 1
            for _id in ids['_ids'].split(','):
                db.cardapios.delete_one({"_id": ObjectId(_id)})
        response = app.response_class(
            response='{} registro(s) removido(s)'.format(count),
            status=200,
            mimetype='application/json'
        )
        return response


@api.route('/editor/editar_notas')
class EditarNotas(Resource):
    def get(self):
        """retorna as notas sobre os cardápios para o frontend"""
        notas = db.notas.find_one({'_id': 1})
        return app.response_class(
            response=json_util.dumps(notas),
            status=200,
            mimetype='application/json'
        )

    def post(self):
        """atualiza as notas sobre os cardápios para o frontend"""
        data = json.loads(request.get_data())
        db.notas.update_one({"_id": 1}, {"$set": data})
        return app.response_class(
            response='editor atualizado com sucesso',
            status=200,
            mimetype='application/json'
        )


@api.route('/migrar_historico_editais')
class MigrarHistoricoEditais(Resource):
    def get(self):
        response = {}
        if 'editais' not in db.collection_names():
            db.create_collection('editais')
            db.editais.insert_many([
                {'nome': '1', 'data_criacao': datetime.now()},
                {'nome': '2', 'data_criacao': datetime.now()},
                {'nome': '3', 'data_criacao': datetime.now()},
                {'nome': '4', 'data_criacao': datetime.now()},
                {'nome': 'EDITAL 78/2016', 'data_criacao': datetime.now()},
                {'nome': 'Novo Edital', 'data_criacao': datetime.now()},
                {'nome': 'Edital 2024', 'data_criacao': datetime.now()}])
            response['editais'] = 'editais criados com sucesso'
        else:
            response['editais'] = 'collection editais já criada'
        if 'escolas_editais' not in db.collection_names():
            db.create_collection('escolas_editais')
            bulk = db.escolas_editais.initialize_ordered_bulk_op()
            escolas = db.escolas.find()
            for escola in escolas:
                bulk.insert({'edital': escola['agrupamento'],
                             'escola': escola['_id'],
                             'data_inicio': '20171218',
                             'data_fim':  None})
            bulk.execute()
            response['escolas_editais'] = 'collection escolas_editais criada com sucesso'
        else:
            response['escolas_editais'] = 'collection escolas_editais já criada'

        return app.response_class(
            response=json_util.dumps(response),
            status=200,
            mimetype='application/json'
        )


@api.route('/migrar_historico_gestao')
class MigrarHistoricoGestao(Resource):
    """Migra gestão das escolas para a tabela de histórico de editais."""
    def get(self):
        response = {}
        if 'escolas_editais' in db.collection_names():
            escolas_terceirizadas = db.escolas.find({'tipo_atendimento': 'TERCEIRIZADA'})
            escolas_terceirizadas_ids = [escola['_id'] for escola in escolas_terceirizadas]
            db.escolas_editais.update_many({'escola': {'$in': escolas_terceirizadas_ids}},
                                           {'$set': {'tipo_atendimento': 'TERCEIRIZADA'}})
            escolas_mistas = db.escolas.find({'tipo_atendimento': 'MISTA'})
            escolas_mistas_ids = [escola['_id'] for escola in escolas_mistas]
            db.escolas_editais.update_many({'escola': {'$in': escolas_mistas_ids}},
                                           {'$set': {'tipo_atendimento': 'MISTA'}})
            escolas_diretas = db.escolas.find({'tipo_atendimento': 'DIRETA'})
            escolas_diretas_ids = [escola['_id'] for escola in escolas_diretas]
            db.escolas_editais.update_many({'escola': {'$in': escolas_diretas_ids}},
                                           {'$set': {'tipo_atendimento': 'DIRETA'}})
            response['escolas_editais'] = 'collection escolas_editais atualizada com tipo_atendimento com sucesso'
        else:
            response['escolas_editais'] = 'collection escolas_editais não existe'
        return app.response_class(
            response=json_util.dumps(response),
            status=200,
            mimetype='application/json'
        )


@api.route('/editor/escolas_editais')
@api.route('/editor/escolas_editais/<string:ids_escolas>')
class EscolasEditais(Resource):
    def get(self, ids_escolas=None):
        if ids_escolas:
            array_ids = [int(e) for e in ids_escolas.split(',')]
            editais = db.escolas_editais.find({'data_fim': None,
                                               'escola': {'$in': array_ids}})
            json_editais_obj = json_util.loads(json_util.dumps(editais))
            escolas_ids = [edital['escola'] for edital in json_editais_obj]
            lista_editais_faltando = list(set(array_ids) - set(escolas_ids))
            for escola in lista_editais_faltando:
                pointer_escola = db.escolas_editais.find_one({'escola': escola})
                json_editais_obj.append(pointer_escola)
            for edital in json_editais_obj:
                del edital['_id']
            json_editais = json.dumps(json_editais_obj)
        else:
            editais = db.escolas_editais.find({'data_fim': None})
            json_editais = json_util.dumps(editais)

        return app.response_class(
            response=json_editais,
            status=200,
            mimetype='application/json'
        )


@api.route('/editor/escolas_editais/criar_escola_edital/<int:id_escola>')
class EscolasEditais(Resource):
    def get(self, id_escola=None):
        response = {}
        if db.escolas_editais.find_one({'escola': id_escola}):
            response['data'] = 'Escola já possui ao menos um edital'
        else:
            escola = db.escolas.find_one({'_id': id_escola})
            db.escolas_editais.insert_one({
                "edital": escola["agrupamento"],
                "escola": id_escola,
                "data_inicio": "20171218",
                "data_fim": None,
                "tipo_atendimento": escola["tipo_atendimento"]
            })
            response['data'] = 'Edital criado com sucesso'
        return app.response_class(
            response=json_util.dumps(response),
            status=200,
            mimetype='application/json'
        )


@api.route('/editor/vigencias_tipo_alimentacao', '/editor/vigencias_tipo_alimentacao/<string:id>')
@api.response(200, 'Lista de vigências de tipo de alimentação ou item específico')
class ListaVigenciasTipoAlimentacao(Resource):
    def get(self, id=None):
        """Retorna lista de vigências ou uma vigência específica se id for informado"""
        fields = {
            '_id': True,
            'data_criacao': True,
            'data_inicio': True,
            'data_fim': True,
            'escola_id': True,
            'escola': True,
            'refeicoes': True
        }
        if id:
            try:
                obj_id = ObjectId(id)
            except Exception:
                obj_id = id

            doc = db.vigencias_tipo_alimentacao.find_one({'_id': obj_id}, fields)
            if not doc:
                return {"message": "Vigência não encontrada"}, 404

            return app.response_class(
                response=json_util.dumps(doc),
                status=200,
                mimetype='application/json'
            )

        query = {}
        if request.args:
            nome_ou_eol = request.args.get('nome', None)
            if nome_ou_eol:
                if any(char.isdigit() for char in nome_ou_eol):
                    eol = extract_digits(nome_ou_eol)
                    query['escola_id'] = str(eol)
                else:
                    nome = extract_chars(nome_ou_eol)
                    query['escola'] = {'$regex': nome.replace(' ', '.*'), '$options': 'i'}
        cursor = db.vigencias_tipo_alimentacao.find(query, fields)
        return app.response_class(
            response=json_util.dumps(cursor),
            status=200,
            mimetype='application/json'
        )


if __name__ == '__main__':
    app.run()
