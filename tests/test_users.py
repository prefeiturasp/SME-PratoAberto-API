import os
import json
from pymongo import MongoClient

API_MONGO_URI = 'mongodb://{}'.format(os.environ.get('API_MONGO_URI'))
client = MongoClient(API_MONGO_URI)
db = client['pratoaberto']


class TestUsers:

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    user_data = {
            'email': 'test@sme.prefeitura.sp.gov.br',
            'senha': '12345'
    }

    def mock_user(self):
        db.usuarios.insert_one(self.user_data)

    def tear_down(self, email):
        query = {'email': email}
        db.usuarios.delete_one(query)

    def test_criar_usuario(self, client):

        url = '/usuarios/novo'

        self.tear_down(self.user_data['email'])
        res = client.post(url, data=json.dumps(self.user_data),
                          headers=self.headers)

        assert res.status_code == 201
        self.tear_down(self.user_data['email'])

    def test_deletar_usuario(self, client):

        url = '/usuario/deletar/test@sme.prefeitura.sp.gov.br'

        self.tear_down(self.user_data['email'])
        self.mock_user()
        res = client.delete(url, headers=self.headers)

        assert res.status_code == 200
        self.tear_down(self.user_data['email'])

    def test_get_usuarios(self, client):

        res = client.get('/usuarios')

        assert res.status_code == 200

    def test_get_usuario(self, client):

        self.tear_down(self.user_data['email'])
        self.mock_user()

        res = client.get('/usuario/test@sme.prefeitura.sp.gov.br')
        assert res.json == [{
                "email": "test@sme.prefeitura.sp.gov.br",
                "senha": "12345"
        }]

        self.tear_down(self.user_data['email'])

    def test_editar_usuario(self, client):

        url = '/usuario/editar/test@sme.prefeitura.sp.gov.br'

        self.tear_down(self.user_data['email'])
        self.mock_user()

        new_user_data = {
                'email': 'test@sme.prefeitura.sp.gov.br',
                'senha': '12345678'
        }

        res = client.put(url, data=json.dumps(new_user_data),
                         headers=self.headers)

        assert res.status_code == 201
        self.tear_down(self.user_data['email'])
