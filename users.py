import os

from flask import make_response, request, jsonify, Blueprint
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

users_api = Blueprint('users_api', __name__)

API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))
client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']
usuarios = db['usuarios']


@users_api.route("/usuarios/novo", methods=['POST'])
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
        db.usuarios.insert_one(usuario)

        response = make_response(jsonify({'HTTP': '201'}), 201)

    return response
