# coding: utf-8
import os

from flask import make_response, request, jsonify, Blueprint
from pymongo import MongoClient,TEXT
from werkzeug.security import generate_password_hash
from bson import json_util

ERRO_DOMINIO = 'Dominio de e-mail nao aceito'
SUCESSO_CRIACAO_USUARIO = 'Usuario criado com sucesso'
ERRO_CRIACAO_USUARIO = 'Nao foi possivel criar esse usuario'
SUCESSO_DELETAR_USUARIO = 'Usuario deletado com sucesso'
ERRO_DELETAR_USUARIO = 'Nao foi possivel deletar esse usuario'
ERRO_RECUPERAR_USUARIOS = 'Nao foi possivel recuperar usuarios'
ERRO_RECUPERAR_USUARIO = 'Nao foi possivel recuperar esse usuario'
ERRO_ATUALIZAR_USUARIO = 'Nao foi possivel atualizar esse usuario'

users_api = Blueprint('users_api', __name__)

# API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))
API_MONGO_URI = 'mongodb://{}'.format('127.0.0.1:27017')
client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']

if "usuarios" in db.collection_names():
    usuarios = db['usuarios']
else:
    usuarios = db.create_collection("usuarios")

if 'email' not in usuarios.index_information():
    usuarios.create_index('email', unique=True)

if 'nome' not in db.escolas.index_information():
    db.escolas.create_index([('nome', 'text')])


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
        response = make_response(jsonify({'erro': ERRO_DOMINIO}), 406)

    else:
        # Criptografa senha
        hs_senha = generate_password_hash(senha, "sha256")

        usuario = {'email': email, 'senha': hs_senha}

        # Verifica excecao de indice do MongoDB
        try:
            db.usuarios.insert(usuario)
            response = make_response(jsonify({'sucesso':
                                             SUCESSO_CRIACAO_USUARIO}), 201)
        except:
            response = make_response(jsonify({'erro':
                                             ERRO_CRIACAO_USUARIO}), 406)

    return response


@users_api.route("/usuario/deletar/<email>", methods=["DELETE"])
def deletar_usuario(email):
    """
    Endpoint para deletar usuario a partir do email
    """
    query = {'email': email}

    try:
        db.usuarios.delete_one(query)
        response = make_response(jsonify({'sucesso':
                                         SUCESSO_DELETAR_USUARIO}), 200)
    except:
        response = make_response(jsonify({'erro':
                                         ERRO_DELETAR_USUARIO}), 406)

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
        response = make_response(jsonify({'erro':
                                         ERRO_RECUPERAR_USUARIOS}), 404)

    return response


@users_api.route("/usuario/<email>", methods=["GET"])
def get_usuario(email):
    """
    Endpoint para recuperar dados de um usuario a partir do email
    """
    query = {'email': email}

    try:
        usuario = db.usuarios.find(query, {'_id': 0})
        response = json_util.dumps(usuario)
    except:
        response = make_response(jsonify({'erro':
                                         ERRO_RECUPERAR_USUARIO}), 404)

    return response


@users_api.route("/usuario/editar/<email>", methods=["PUT"])
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
        response = make_response(jsonify({'erro':
                                         ERRO_ATUALIZAR_USUARIO}), 406)

    response = make_response(jsonify({'HTTP': '201'}), 201)

    return response
