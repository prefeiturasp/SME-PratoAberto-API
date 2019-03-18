# -*- coding: utf-8 -*-
import json
import math
import os
import time
from datetime import datetime
from dateutil.parser import parse

from bson import json_util, ObjectId
from flask import Flask, request, render_template, send_file, Response
from flask_restplus import Api, Resource
from pymongo import MongoClient
from xhtml2pdf import pisa
import utils

from utils import (sort_cardapio_por_refeicao,
                   remove_refeicao_duplicada_sme_conv,
                   extract_digits,
                   extract_chars)

app = Flask(__name__)
api = Api(app, default='API do Prato Aberto', default_label='endpoints para se comunicar com a API do Prato Aberto')

API_KEY = os.environ.get('API_KEY')
# API_MONGO_URI = 'mongodb://localhost:27017'
API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))
client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']

with open('de_para.json', 'r') as f:
    conf = json.load(f)
    refeicoes = conf['refeicoes']
    idades = conf['idades']
    idades_reversed = {v: k for k, v in conf['idades'].items()}


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
        if escola:
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
            category_dict[age] = day['cardapio'].keys()

    return category_dict


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

    return new_list_category


def filter_by_menu_school(menu_organizes, menu_type_by_school):
    new_dict_menu = {}
    for keys, values in menu_organizes.items():
        new_dict_menu[keys] = []
        for val in values:
            for v in val['cardapio']:
                if v in menu_type_by_school:
                    new_dict_menu[keys].append(val)

    return new_dict_menu


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
        response_menu = find_menu_json(request, data)
        response = {}

        menu_type_by_school = _get_school_by_name(request.args.get('nome'))

        formated_data = _reorganizes_data_menu(response_menu)
        date_organizes = _reorganizes_date(formated_data)
        catergory_ordered = _reorganizes_category(formated_data)
        menu_organizes = _reorganizes_menu_week(formated_data)

        inicio = datetime.strptime(request.args.get('data_inicial'), '%Y%m%d')
        fim = datetime.strptime(request.args.get('data_final'), '%Y%m%d')

        current_date = self._get_current_date(inicio, fim)
        response['school_name'] = request.args.get('nome')
        response['response'] = response_menu
        response['week_menu'] = current_date

        cpath = os.path.realpath(os.path.dirname(__file__)) + '/static/'

        wipe_unused(cpath, 5)

        # teste = filter_by_menu_school(menu_organizes, menu_type_by_school)

        html = render_template('cardapio-pdf.html', resp=response, descriptions=formated_data, dates=date_organizes,
                               categories=catergory_ordered, menus=menu_organizes)
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
    name = 'cardapio_mensal_{}.pdf'.format(datetime.strftime(today, '%d_%m_%Y_%H_%M_%S'))
    filename = os.path.join(path, name)

    resultFile = open(filename, "w+b")

    # convert HTML to PDF
    pisa.CreatePDF(pdf_data, dest=resultFile)  # file handle to recieve result

    # close output file
    resultFile.close()

    return filename


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
    for value in data_dict:
        if value['idade'] in key_dict.keys():
            key_dict[value['idade']].append({'data': _converter_to_date(value['data']), 'cardapio': value['cardapio'],
                                             'publicacao': _set_datetime(value['data_publicacao'])})
    return key_dict


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
    atime_limit = time.time() - limit
    count = 0
    for filename in os.listdir(basedir):
        path = os.path.join(basedir, filename)
        if os.path.getatime(path) < atime_limit:
            os.remove(path)
            count += 1
    print("Removed {} files.".format(count))


def find_menu_json(request_data, data):
    """ Return json's menu from a school """
    query = {
        'status': 'PUBLICADO'
    }
    if request_data.args.get('agrupamento'):
        query['agrupamento'] = request_data.args['agrupamento']
    if request_data.args.get('tipo_atendimento'):
        query['tipo_atendimento'] = request_data.args['tipo_atendimento']
    if request_data.args.get('tipo_unidade'):
        query['tipo_unidade'] = request_data.args['tipo_unidade']
    if request_data.args.get('idade'):
        query['idade'] = idades_reversed.get(request_data.args['idade'])
    if data:
        query['data'] = data
    else:
        data = {}
        if request_data.args.get('data_inicial'):
            data.update({'$gte': request_data.args['data_inicial']})
        if request_data.args.get('data_final'):
            data.update({'$lte': request_data.args['data_final']})
        if data:
            query['data'] = data
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
                           'D - 6 MESES', 'D - 7 MESES', 'E - 8 A 11 MESES', 'X - 1A -1A E 11MES', 'F - 2 A 3 ANOS',
                           'G - 4 A 6 ANOS', 'I - 2 A 6 ANOS', 'W - EMEI DA CEMEI', 'N - 6 A 7 MESES PARCIAL',
                           'O - 8 A 11 MESES PARCIAL', 'Y - 1A -1A E 11MES PARCIAL', 'P - 2 A 3 ANOS PARCIAL',
                           'Q - 4 A 6 ANOS PARCIAL', 'H - ADULTO', 'Z - UNIDADES SEM FAIXA', 'S - FILHOS PRO JOVEM',
                           'V - PROFESSOR', 'U - PROFESSOR JANTAR CEI']

    for c in cardapios:
        _cardapios.append(c)
    for i in definicao_ordenacao:
        for c in _cardapios:
            if i == c['idade']:
                cardapio_ordenado.append(c)
                continue

    for c in cardapio_ordenado:
        try:
            c['idade'] = idades[c['idade']]
            c['cardapio'] = {refeicoes[k]: v for k, v in c['cardapio'].items()}
        except KeyError as e:
            app.logger.debug('erro de chave: {} objeto {}'.format(str(e), c))

    for c in cardapio_ordenado:
        c['cardapio'] = sort_cardapio_por_refeicao(c['cardapio'])

    if query['tipo_unidade'] == 'SME_CONVÊNIO':
        cardapio_ordenado = remove_refeicao_duplicada_sme_conv(cardapio_ordenado)

    return cardapio_ordenado


@api.route('/editor/cardapios')
class CardapiosEditor(Resource):
    def get(self):
        """retorna os cardápios para o editor"""
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)
        query = {}
        if request.args.get('status'):
            query['status'] = {'$in': request.args.getlist('status')}
        else:
            query['status'] = 'PUBLICADO'
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
            try:
                _id = item['_id']
                bulk.find({'_id': _id}).update({'$set': item})
            except:
                bulk.insert(item)
        bulk.execute()
        return ('', 200)


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


if __name__ == '__main__':
    # app.run(port=7000, debug=True)
    app.run()
