import os

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import json_util
from bson.objectid import ObjectId


app = Flask(__name__)

API_KEY = os.environ.get('API_KEY')
API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))

client = MongoClient(API_MONGO_URI)
try:
    # The ismaster command is cheap and does not require auth.
    client.admin.command('ismaster')
    print('mongo connected')
except ConnectionFailure:
    print('mongo not available')
db = client['pratoaberto']


@app.route('/escolas')
def get_lista_escolas():
    try:
        # busca por nome
        nome = request.args['nome']
        # to-do: adicionar idades da escola a resposta
        cursor = db.escolas.find(
            { 'nome': { '$regex': nome.replace(' ', '.*'), '$options': 'i' } },
            { '_id': True, 'nome': True }).limit(int(request.args.get('limit', 5)))
    except KeyError:
        if 'completo' not in request.args:
            fields =  {
                'tipo_unidade': False,
                'tipo_atendimento': False,
                'agrupamento': False,
                'telefone': False
            }
            cursor = db.escolas.find({}, fields)
        else:
            cursor = db.escolas.find({})

    response = app.response_class(
        response=json_util.dumps(cursor),
        status=200,
        mimetype='application/json'
    )
    return response


@app.route('/escola/<int:id_escola>')
def get_detalhe_escola(id_escola):
    escola = db.escolas.find_one({'_id': id_escola}, {'_id': False})
    if escola:
        pipeline = [
            { "$limit": 100 },
            { "$match": { "tipo_unidade": escola['tipo_unidade'] } },
            { "$group": { "_id": "$tipo_unidade", "idades": { "$addToSet": "$idade" } } },
            { "$project": { "_id": False, "idades": True } }
        ]
        idades = list(db.cardapios.aggregate(pipeline))
        try:
            escola['idades'] = idades[0]['idades']
        except:
            escola['idades'] = ['UNIDADE SEM FAIXA']
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
            query['idade'] = request.args['idade']

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

        cardapios = db.cardapios.find(query, fields).sort([('data', -1)])

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
        query['idade'] = request.args['idade']

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

    response = app.response_class(
        response=json_util.dumps(cardapios),
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
        for item in json_util.loads(request.data):
            try:
                _id = item['_id']
                bulk.find({'_id': _id}).update({'$set': item})
            except:
                bulk.insert(item)
        bulk.execute()
        return ('', 200)


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
        { '_id': id_escola },
        { '$set': payload },
        upsert=False)
    return ('', 200)


if __name__ == '__main__':
    client = MongoClient('mongodb://localhost:27017')
    db = client['pratoaberto']
    app.run(debug=True)

