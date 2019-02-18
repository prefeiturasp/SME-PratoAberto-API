# -*- coding: utf-8 -*-
import json
import math
import os
from datetime import datetime

from bson import json_util, ObjectId
from flask import Flask, request, render_template
from pymongo import MongoClient
from flask_weasyprint import HTML, render_pdf

from utils import (sort_cardapio_por_refeicao,
                   remove_refeicao_duplicada_sme_conv,
                   extract_digits,
                   extract_chars)

app = Flask(__name__)

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


@app.route('/report.pdf')
@app.route('/report/<data>')
def report_menu(data=None):
    response_menu = __find_menu_json(request, data)
    response = {}

    inicio = datetime.strptime(request.args.get('data_inicial'),'%Y%m%d')
    fim = datetime.strptime(request.args.get('data_final'),'%Y%m%d')

    response['inicio'] = datetime.strftime(inicio,'%d/%m/%Y')
    response['fim'] = datetime.strftime(fim,'%d/%m/%Y')
    response['response'] = response_menu


    html = render_template('report.html',menu=response)
    return render_pdf(HTML(string=html))


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
    # app.run(port=7000, debug=True, host='127.0.0.1')
    app.run()
