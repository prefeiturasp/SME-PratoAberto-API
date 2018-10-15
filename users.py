import os

from flask import make_response, request, jsonify, Blueprint
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util
from functools import wraps
from flask import Response

users_api = Blueprint('users_api', __name__)

API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))
client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']

if "usuarios" in db.collection_names():
    usuarios = db['usuarios']
else:
    usuarios = db.create_collection("usuarios")

index_name = 'email'
if index_name not in usuarios.index_information():
    usuarios.create_index(index_name, unique=True)


def check_autenticacao(email, senha):
    """
    Funcao para checar combinacao de username e password
    """
    query = {'email': email}

    try:
        usuario = db.usuarios.find_one(query, {'_id': 0})
    except:
        return False

    return email == usuario['email'] and check_password_hash(usuario['senha'], senha)


def requer_autenticacao(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_autenticacao(auth.username, auth.password):
            return Response('Could not verify your access level for that URL.\n'
                            'You have to login with proper credentials', 401,
                            {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated


@users_api.route("/usuarios/novo", methods=["POST"])
def criar_usuario():
    """
    Endpoint para criação de usuário
    """
    email = request.json['email']
    senha = request.json['senha']

    # Valida email de acordo com padrao da prefeitura
    dominio = email.split("@")[1]
    if (dominio != "sme.prefeitura.sp.gov.br"):
        response = make_response(jsonify({'erro': 'Dominio de e-mail nao aceito'}), 406)

    else:
        # Criptografa senha
        hs_senha = generate_password_hash(senha, "sha256")

        usuario = {'email': email, 'senha': hs_senha}

        # Verifica excecao de indice do MongoDB
        try:
            db.usuarios.insert_one(usuario)
            response = make_response(jsonify({'sucesso': 'Usuario criado com sucesso'}), 201)
        except:
            response = make_response(jsonify({'erro': 'Nao foi possivel criar esse usuario'}), 406)

    return response


@users_api.route("/usuario/deletar/<email>", methods=["DELETE"])
@requer_autenticacao
def deletar_usuario(email):
    """
    Endpoint para deletar usuario a partir do email
    """
    query = {'email': email}

    try:
        db.usuarios.delete_one(query)
        response = make_response(jsonify({'sucesso': 'Usuario deletado com sucesso'}), 200)
    except:
        response = make_response(jsonify({'erro': 'Nao foi possivel deletar esse usuario'}), 406)

    return response


@users_api.route("/usuarios", methods=["GET"])
def get_usuarios():
    """
    Endpoint para listar usuarios da API
    """
    try:
        usuarios = db.usuarios.find()
        response = json_util.dumps(usuarios)
    except:
        response = make_response(jsonify({'erro': 'Nao foi possivel recuperar usuarios'}), 404)

    return response


@users_api.route("/usuario/<email>", methods=["GET"])
@requer_autenticacao
def get_usuario(email):
    """
    Endpoint para recuperar dados de um usuario a partir do email
    """
    query = {'email': email}

    try:
        usuario = db.usuarios.find(query, {'_id': 0})
        response = json_util.dumps(usuario)
    except:
        response = make_response(jsonify({'erro': 'Nao foi possivel recuperar esse usuario'}), 404)

    return response


@users_api.route("/usuario/editar/<email>", methods=["PUT"])
@requer_autenticacao
def editar_usuario(email):
    """
    Endpoint para editar dados de um usuario a partir do email
    """
    query = {'email': email}

    senha = request.json['senha']
    hs_senha = generate_password_hash(senha, "sha256")

    try:
        dados_atualizados = {'$set': {'senha': hs_senha}}
        db.usuarios.update_one(query, dados_atualizados)
    except:
        response = make_response(jsonify({'erro': 'Nao foi possivel atualizar esse usuario'}), 406)

    response = make_response(jsonify({'HTTP': '201'}), 201)

    return response
