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
                   remove_refeicao_duplicada_sme_conv)

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
                    escola['refeicoes'] = [refeicoes.get(x, x) for x in escola['refeicoes']]
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


def _reorganizes_category(menu_dict):
    category_dict = {}
    for age, menu in menu_dict.items():
        for day in menu:
            categories = list(day['cardapio'].keys())
            category_dict[age] = _change_order_categories_list(categories)

    return category_dict


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

    return new_list_category, school[0]['idades']


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

        menu_type_by_school, _ = _get_school_by_name(request.args.get('nome'))

        formated_data = _reorganizes_data_menu(response_menu)
        date_organizes = _reorganizes_date(formated_data)
        catergory_ordered = _reorganizes_category(formated_data)

        menu_organizes = _reorganizes_menu_week(formated_data)

        filtered_category_ordered = filter_by_menu_school(catergory_ordered, menu_type_by_school)

        inicio = datetime.strptime(request.args.get('data_inicial'), '%Y%m%d')
        fim = datetime.strptime(request.args.get('data_final'), '%Y%m%d')

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

    edital_corrente = db.escolas_editais.find_one(
        {'escola': int(school_id), '$or': [{'data_fim': {'$gte': str(dia)}}, {'data_fim': None}]})

    edital_corrente_nome = edital_corrente['edital'] if edital_corrente else 'EDITAL 78/2016'
    tipo_gestao_corrente = edital_corrente['tipo_atendimento'] if edital_corrente else 'TERCEIRIZADA'

    query['agrupamento'] = edital_corrente_nome if not unidade_especial else 'UE'
    if request_data.args.get('tipo_atendimento'):
        query['tipo_atendimento'] = tipo_gestao_corrente if not unidade_especial else 'UE'
    if request_data.args.get('tipo_unidade'):
        query['tipo_unidade'] = request_data.args['tipo_unidade'] if not unidade_especial else unidade_especial['nome']
    if request_data.args.get('idade'):
        query['idade'] = idades_reversed.get(request_data.args['idade'])
    if dia:
        query['data'] = dia
    else:
        dia = {}
        if request_data.args.get('data_inicial'):
            dia.update({'$gte': request_data.args['data_inicial']})
        if request_data.args.get('data_final'):
            dia.update({'$lte': request_data.args['data_final']})
        if dia:
            query['data'] = dia
    limit = int(request_data.args.get('limit', 0))
    page = int(request_data.args.get('page', 0))
    fields = {
        '_id': False,
        'status': False,
        'cardapio_original': False,
    }
    cardapios = db.cardapios.find(query, fields).sort([('data', -1)])
    if page and limit:
        cardapios = cardapios.skip(limit * (page - 1)).limit(limit)
    elif limit:
        cardapios = cardapios.limit(limit)
    _cardapios = []
    cardapio_ordenado = []
    definicao_ordenacao = ['A - 0 A 1 MES', 'B - 1 A 3 MESES', 'C - 4 A 5 MESES', 'D - 0 A 5 MESES', 'D - 6 A 7 MESES',
                           'D - 6 MESES', 'D - 7 MESES', 'E - 7 A 11 MESES', 'E - 8 A 11 MESES', 'X - 1A -1A E 11MES',
                           'F - 1 A 3 ANOS', 'F - 2 A 3 ANOS', 'G - 4 A 6 ANOS', 'I - 2 A 6 ANOS', 'W - EMEI DA CEMEI',
                           'N - 6 A 7 MESES PARCIAL', 'O - 8 A 11 MESES PARCIAL', 'Y - 1A -1A E 11MES PARCIAL',
                           'P - 2 A 3 ANOS PARCIAL', 'Q - 4 A 6 ANOS PARCIAL', 'H - ADULTO', 'Z - UNIDADES SEM FAIXA',
                           'S - FILHOS PRO JOVEM', 'V - PROFESSOR', 'U - PROFESSOR JANTAR CEI']
    category_by_school = None
    school_ages = None

    if request_data.args.get('nome'):
        category_by_school, school_ages = _get_school_by_name(request_data.args.get('nome'))

    for c in cardapios:
        _cardapios.append(c)

    for i in definicao_ordenacao:
        for c in _cardapios:
            if i == c['idade'] and i in school_ages:
                cardapio_ordenado.append(c)
                continue

    for c in cardapio_ordenado:
        try:
            c['idade'] = idades[c['idade']]
            c['cardapio'] = {refeicoes[k]: v for k, v in c['cardapio'].items()}
            if category_by_school:
                c['cardapio'] = {k: v for k, v in c['cardapio'].items() if k in category_by_school}
        except KeyError as e:
            app.logger.debug('erro de chave: {} objeto {}'.format(str(e), c))

    for c in cardapio_ordenado:
        c['cardapio'] = sort_cardapio_por_refeicao(c['cardapio'])

    if query['tipo_unidade'] == 'SME_CONVÊNIO' and len(cardapio_ordenado):
        cardapio_ordenado = remove_refeicao_duplicada_sme_conv(cardapio_ordenado)

    return cardapio_ordenado


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
                {'nome': 'Novo Edital', 'data_criacao': datetime.now()}])
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
            editais = db.escolas_editais.find({'data_fim': None,
                                               'escola': {'$in': [int(e) for e in ids_escolas.split(',')]}})
        else:
            editais = db.escolas_editais.find({'data_fim': None})
        return app.response_class(
            response=json_util.dumps(editais),
            status=200,
            mimetype='application/json'
        )


if __name__ == '__main__':
    app.run()
