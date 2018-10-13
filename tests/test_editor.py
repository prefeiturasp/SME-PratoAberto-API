import json


class TestEditor:

    def test_get_cardapios_editor(self, client):
        res = client.get('/editor/cardapios')
        assert res.status_code == 200

    def test_get_escolas_editor(self, client):
        res = client.get('/editor/escolas')
        assert res.status_code == 200

    def test_post_escolas_editor(self, client):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        data = {
                "nome": "EMEI PAULO CAMILHIER FLORENCANO - (TERCEI.)",
                "telefone": "(11)25578348",
                "idades": ["Z - UNIDADES SEM FAIXA"],
                "endereco": "R. FELICIANO DE MENDONCA, 502",
                "lon": -46.398452, "lat": -23.553905,
                "tipo_atendimento": "TERCEIRIZADA",
                "status": "inativo",
                "edital": "EDITAL 78/2016",
                "agrupamento": "EDITAL 78/2016",
                "_id": 86,
                "tipo_unidade": "EMEI",
                "agrupamento_regiao": 2,
                "bairro": "GUAIANASES",
                "refeicoes": ["L5 - LANCHE 5 HORAS", "R1 - REFEICAO 1"]
                }

        url = '/editor/escola/86'

        res = client.post(url, data=json.dumps(data), headers=headers)

        assert res.status_code == 200

    def test_post_invalido_escolas_editor(self, client):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        data = {"name": "EMEI PAULO CAMILHIER FLORENCANO - (TERCEI.)"}

        url = '/editor/escola/86'

        res = client.post(url, data=json.dumps(data), headers=headers)

        assert res.status_code == 500
