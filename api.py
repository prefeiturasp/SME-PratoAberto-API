# -*- coding: utf-8 -*-
import json
import os

from flask import Flask, request
from pymongo import MongoClient
from bson import json_util
from users import users_api

app = Flask(__name__)
app.register_blueprint(users_api)
API_KEY = os.environ.get('API_KEY')
API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))

client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']


def create_app():

    app = Flask(__name__)

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
            query['nome'] = { '$text': { '$search': nome, '$language': 'pt', '$caseSensitive': False, '$diacriticSensitive': False } }
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
        if 'idades' in escola:
            escola['idades'] = [idades.get(x, x) for x in escola['idades']]
        if 'refeicoes' in escola:
            escola['refeicoes'] = [refeicoes.get(x, x) for x in escola['refeicoes']]
        if escola:
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
        query = {
            'status': 'PUBLICADO'
        }

        if request.args.get('agrupamento'):
            query['agrupamento'] = request.args['agrupamento']
        if request.args.get('tipo_atendimento'):
            query['tipo_atendimento'] = request.args['tipo_atendimento']
        if request.args.get('tipo_unidade'):
            query['tipo_unidade'] = request.args['tipo_unidade']
        if request.args.get('idade'):
            query['idade'] = idades_reversed.get(request.args['idade'])

        if data:
            query['data'] = data
        else:
            data = {}
            if request.args.get('data_inicial'):
                data.update({'$gte': request.args['data_inicial']})
            if request.args.get('data_final'):
                data.update({'$lte': request.args['data_final']})
            if data:
                query['data'] = data

        limit = int(request.args.get('limit', 0))
        page = int(request.args.get('page', 0))

        fields = {
            '_id': False,
            'status': False,
            'cardapio_original': False,
        }

        cardapios = db.cardapios.find(query, fields).sort([('data', -1)])
        if page and limit:
            cardapios = cardapios.skip(limit*(page-1)).limit(limit)
        elif limit:
            cardapios = cardapios.limit(limit)

        _cardapios = []
        cardapio_ordenado = []
        definicao_ordenacao = ['A - 0 A 1 MES','B - 1 A 3 MESES','C - 4 A 5 MESES','D - 0 A 5 MESES','D - 6 A 7 MESES','D - 6 MESES','D - 7 MESES','E - 8 A 11 MESES','X - 1A -1A E 11MES','F - 2 A 3 ANOS','G - 4 A 6 ANOS','I - 2 A 6 ANOS','W - EMEI DA CEMEI','N - 6 A 7 MESES PARCIAL','O - 8 A 11 MESES PARCIAL','Y - 1A -1A E 11MES PARCIAL','P - 2 A 3 ANOS PARCIAL','Q - 4 A 6 ANOS PARCIAL','H - ADULTO','Z - UNIDADES SEM FAIXA','S - FILHOS PRO JOVEM','V - PROFESSOR','U - PROFESSOR JANTAR CEI']

        for c in cardapios:
            _cardapios.append(c)

        for i in definicao_ordenacao:
            for c in _cardapios:
                if i == c['idade']:
                    cardapio_ordenado.append(c)
                    continue

        for c in cardapio_ordenado:
            c['idade'] = idades[c['idade']]
            c['cardapio'] = {refeicoes[k]: v for k, v in c['cardapio'].items()}

        for c in cardapio_ordenado:
            for x in refeicoes:
                if refeicoes[x] in c['cardapio']:
                    c['cardapio'][refeicoes[x]] = sorted(c['cardapio'][refeicoes[x]])

        response = app.response_class(
            response=json_util.dumps(cardapio_ordenado),
            status=200,
            mimetype='application/json'
        )
        return response

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
                cardapios = cardapios.skip(limit*(page-1)).limit(limit)
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
        cursor = db.escolas.find(query)

        response = app.response_class(
            response=json_util.dumps(cursor),
            status=200,
            mimetype='application/json'
        )
        return response

    @app.route('/editor/escola/<int:id_escola>', methods=['POST'])
    def edit_escola(id_escola):
        key = request.headers.get('key')
        if key != API_KEY:
            return ('', 401)

        try:
            payload = json_util.loads(request.data)
        except:
            return app.response_class(
                response=json_util.dumps({'erro': 'Dados POST não é um JSON válido'}),
                status=500,
                mimetype='application/json'
            )

        db.escolas.update_one(
            {'_id': id_escola},
            {'$set': payload},
            upsert=False)
        return ('', 200)

    @app.route('/status')
    def get_api_status():
        return app.response_class(
            response=json_util.dumps({'status': 'ativo'}),
            status=200,
            mimetype='application/json'
        )

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', debug=True)
