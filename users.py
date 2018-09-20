import os

from flask import make_response, request, jsonify, Blueprint
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from bson import json_util

users_api = Blueprint('users_api', __name__)

API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))
client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']

if "usuarios" in db.collection_names():
    usuarios = db['usuarios']
else:
    usuarios = db.createCollection("usuarios")

index_name = 'email'
if index_name not in usuarios.index_information():
    usuarios.create_index(index_name, unique=True)


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
        response = make_response(jsonify({'HTTP': '406'}), 406)

    else:
        # Criptografa senha
        hs_senha = generate_password_hash(senha, "sha256")

        usuario = {'email': email, 'senha': hs_senha}

        # Verifica excecao de indice do MongoDB
        try:
            db.usuarios.insert_one(usuario)
            response = make_response(jsonify({'HTTP': '201'}), 201)
        except:
            response = make_response(jsonify({'HTTP': '406'}), 406)

    return response


@users_api.route("/usuario/deletar/<email>", methods=["DELETE"])
def deletar_usuario(email):
    """
    Endpoint para deletar usuario a partir do email
    """
    query = {'email': email}

    db.usuarios.delete_one(query)
    response = make_response(jsonify({'HTTP': '201'}), 201)

    return response


@users_api.route("/usuarios", methods=["GET"])
def get_usuarios():
    """
    Endpoint para listar usuarios da API
    """
    usuarios = db.usuarios.find()
    response = json_util.dumps(usuarios)

    return response


@users_api.route("/usuario/<email>", methods=["GET"])
def get_usuario(email):
    """
    Endpoint para recuperar dados de um usuario a partir do email
    """
    query = {'email': email}

    usuario = db.usuarios.find(query)
    response = json_util.dumps(usuario)

    return response


@users_api.route("/usuario/editar/<email>", methods=["PUT"])
def editar_usuario(email):
    """
    Endpoint para editar dados de um usuario a partir do email
    """
    query = {'email': email}

    senha = request.json['senha']
    hs_senha = generate_password_hash(senha, "sha256")

    dados_atualizados = {'$set': {'senha': hs_senha}}
    db.usuarios.update_one(query, dados_atualizados)

    response = make_response(jsonify({'HTTP': '201'}), 201)

    return response
