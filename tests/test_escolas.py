class TestEscolas:

    def test_get_escolas(self, client):
        res = client.get('/escolas')
        assert res.status_code == 200

    def test_get_detalhe_escola(self, client):
        res = client.get('/escola/418')
        assert res.status_code == 200
        assert res.json == {"nome":
                            "EMEF PROF. JO\u00c3O SOUZA FERRAZ - (MIST)",
                            "telefone": "(11)56114691",
                            "idades": ["Todas as idades", "Toda Idade"],
                            "endereco": "R. RAFAEL CORREIA SAMPAIO, 291",
                            "lon": -46.675494,
                            "lat": -23.689499,
                            "tipo_atendimento": "MISTA",
                            "agrupamento": 1,
                            "tipo_unidade": "EMEF",
                            "agrupamento_regiao": 1,
                            "bairro": "JD. PALMARES",
                            "refeicoes":
                            ["Lanche - Perman\u00eancia de 5 ou 6 horas",
                             "Refei\u00e7\u00e3o"]}

    def test_get_detalhe_escola_inexistente(self, client):
        res = client.get('/escola/1')
        assert res.status_code == 404
        assert res.json == {'erro': 'Escola inexistente'}
