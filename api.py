# -*- coding: utf-8 -*-
import json
import math
import os
from datetime import datetime

from bson import json_util, ObjectId
from flask import Flask, request, render_template, send_file
from pymongo import MongoClient
from xhtml2pdf import pisa
import utils

from utils import (sort_cardapio_por_refeicao,
                   remove_refeicao_duplicada_sme_conv,
                   extract_digits,
                   extract_chars)

app = Flask(__name__)

API_KEY = os.environ.get('API_KEY')
API_MONGO_URI = 'mongodb://localhost:27017'
# API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))
client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']

with open('de_para.json', 'r') as f:
    conf = json.load(f)
    refeicoes = conf['refeicoes']
    idades = conf['idades']
    idades_reversed = {v: k for k, v in conf['idades'].items()}


@app.route('/escolas')
def get_lista_escolas():
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


@app.route('/escola/<int:id_escola>')
def get_detalhe_escola(id_escola):
    query = {'_id': id_escola, 'status': 'ativo'}
    fields = {'_id': False, 'status': False}
    escola = db.escolas.find_one(query, fields)
    if escola:
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


@app.route('/escola/<int:id_escola>/cardapios')
@app.route('/escola/<int:id_escola>/cardapios/<data>')
def get_cardapio_escola(id_escola, data=None):
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


@app.route('/cardapios')
@app.route('/cardapios/<data>')
def get_cardapios(data=None):
    cardapio_ordenado = __find_menu_json(request, data)

    response = app.response_class(
        response=json_util.dumps(cardapio_ordenado),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/test-report-templates')
def test_report_template():
    return render_template('teste.html')


def _filter_category(descriptions):
    category_dict = {}

    for age, day in descriptions.items():
        for day, menu in day.items():
            category_dict[age] = menu.keys()
    return category_dict


@app.route('/report')
@app.route('/report/<data>')
def report_menu(data=None):
    response_menu = __find_menu_json(request, data)
    response = {}
    all_menu_information = __create_menu_list(response_menu)

    _reorganizes_data_menu(response_menu)

    inicio = datetime.strptime(request.args.get('data_inicial'), '%Y%M%d')
    fim = datetime.strptime(request.args.get('data_final'), '%Y%m%d')

    current_date = '{} a {} de {} de {}'.format(inicio.day, fim.day, utils.translate_date_month(inicio.month), fim.year)
    response['school_name'] = response_menu[0]['tipo_unidade'].replace('_', ' ')
    response['response'] = response_menu
    response['week_menu'] = current_date

    category_filtered = _filter_category(all_menu_information)

    html = render_template('report.html', menu=response, descriptions=all_menu_information,
                           categories=category_filtered)
    return html
    # pdf = _create_pdf(html)
    # pdf_name = pdf.split('/')[-1]
    #
    # return send_file(pdf, mimetype=pdf_name)


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


@app.route('/cardapio-pdf')
@app.route('/cardapio-pdf/<data>')
def report_pdf(data=None):
    response_menu = __find_menu_json(request, data)
    response = {}

    formated_data = _reorganizes_data_menu(response_menu)
    date_organizes = _reorganizes_date(formated_data)
    catergory_ordered = _reorganizes_category(formated_data)

    inicio = datetime.strptime(request.args.get('data_inicial'), '%Y%M%d')
    fim = datetime.strptime(request.args.get('data_final'), '%Y%m%d')



    current_date = '{} a {} de {} de {}'.format(inicio.day, fim.day, utils.translate_date_month(inicio.month), fim.year)
    response['school_name'] = response_menu[0]['tipo_unidade'].replace('_', ' ')
    response['response'] = response_menu
    response['week_menu'] = current_date

    html = render_template('cardapio-pdf.html', resp=response, descriptions=formated_data, dates=date_organizes,
                           categories=catergory_ordered)
    return html
    # pdf = _create_pdf(html)
    # pdf_name = pdf.split('/')[-1]
    #
    # return send_file(pdf, mimetype=pdf_name)


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
    # pdf = BytesIO()
    # pisa.CreatePDF(src=pdf_data,dest='static/')
    # return pdf
    # open output file for writing (truncated binary)
    today = datetime.now()

    cdir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(cdir, 'static')
    name = 'cardapio_mensal_{}.pdf'.format(datetime.strftime(today, '%d_%m_%Y_%H_%M_%S'))
    filename = os.path.join(path, name)

    resultFile = open(filename, "w+b")

    # convert HTML to PDF
    pisaStatus = pisa.CreatePDF(pdf_data, dest=resultFile)  # file handle to recieve result

    # close output file
    resultFile.close()

    return filename


# Reorganizes datas from menu week

def __create_menu_list(data_dict):
    date_from_week = __assemble_list_date_week(data_dict)
    date_from_age = __assemble_list_age(data_dict)

    date_with_menu = {}
    date_with_age = {}
    for data in data_dict:
        for age in date_from_age:
            for day in date_from_week:
                if age in data['idade'] and day in data['data']:
                    date_with_menu[day] = data['cardapio']
                    date_with_age[age] = date_with_menu

    return date_with_age


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
            key_dict[value['idade']].append({'data': _converter_to_date(value['data']), 'cardapio': value['cardapio']})
    return key_dict


def _converter_to_date(str_date):
    return datetime.strptime(str_date, '%Y%m%d')


def __assemble_list_date_week(data_dict):
    date_week_list = []

    for day in data_dict:
        if day['data'] not in date_week_list:
            date_week_list.append(day['data'])

    return sorted(date_week_list)


def __assemble_list_age(data_dict):
    age_menu_list = []

    for age in data_dict:
        if age['idade'] not in age_menu_list:
            age_menu_list.append(age['idade'])

    return age_menu_list


def __find_menu_json(request_data, data):
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


@app.route('/editor/cardapios', methods=['GET', 'POST'])
def get_cardapios_editor():
    key = request.headers.get('key')
    if key != API_KEY:
        return ('', 401)

    if request.method == 'GET':
        query = {}

        if request.args.get('status'):
            query['status'] = {'$in': request.args.getlist('status')}
        else:
            query['status'] = 'PUBLICADO'
        if request.args.get('agrupamento'):
            query['agrupamento'] = request.args['agrupamento']
        if request.args.get('tipo_atendimento'):
            query['tipo_atendimento'] = request.args['tipo_atendimento']
        if request.args.get('tipo_unidade'):
            query['tipo_unidade'] = request.args['tipo_unidade']
        if request.args.get('idade'):
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

    elif request.method == 'POST':
        bulk = db.cardapios.initialize_ordered_bulk_op()
        for item in json_util.loads(request.data.decode("utf-8")):
            try:
                _id = item['_id']
                bulk.find({'_id': _id}).update({'$set': item})
            except:
                bulk.insert(item)
        bulk.execute()
        return ('', 200)


@app.route('/editor/escolas')
def get_escolas_editor():
    key = request.headers.get('key')
    if key != API_KEY:
        return ('', 401)

    query = {'status': 'ativo'}
    if request.args:
        nome = extract_chars(request.args['nome'])
        eol = extract_digits(request.args['nome'])
        if eol:
            query['_id'] = eol
        else:
            query['nome'] = {'$regex': nome.replace(' ', '.*'), '$options': 'i'}
        if request.args['agrupamento'] != 'TODOS':
            query['agrupamento'] = request.args['agrupamento']
        if request.args['tipo_atendimento'] != 'TODOS':
            query['tipo_atendimento'] = request.args['tipo_atendimento']

    cursor = db.escolas.find(query).limit(200)

    response = app.response_class(
        response=json_util.dumps(cursor),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/v2/editor/escolas')
def v2_get_escolas_editor():
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


@app.route('/editor/escola/<int:id_escola>', methods=['POST', 'DELETE'])
def edit_escola(id_escola):
    key = request.headers.get('key')
    if key != API_KEY:
        return ('', 401)
    if request.method == 'DELETE':
        db.escolas.delete_one(
            {'_id': id_escola})
        return ('', 200)
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


@app.route('/editor/remove-cardapio', methods=['POST'])
def remove_cardapios():
    if request.method == 'POST':

        '''Convert params to disct'''
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


if __name__ == '__main__':
    app.run(port=7000, debug=True)
    # app.run()
