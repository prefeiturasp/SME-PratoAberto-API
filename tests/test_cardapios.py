class TestCardapios:

    def test_get_cardapios(self, client):
        res = client.get('/cardapios')
        assert res.status_code == 200

    def test_get_cardapio_escola(self, client):
        res = client.get('/escola/418/cardapios')
        assert res.status_code == 200

    def test_get_cardapio_escola_inexistente(self, client):
        res = client.get('/escola/1/cardapios')
        assert res.status_code == 404

    def test_get_cardapio_escola_inexistente_messagem(self, client):
        res = client.get('/escola/1/cardapios')
        assert res.json == {'erro': 'Escola inexistente'}

    def test_get_cardapio_escola_por_data(self, client):
        res = client.get('/escola/418/cardapios/20180622')
        assert res.status_code == 200

    def test_get_cardapio_escola_com_data_inexistente(self, client):
        res = client.get('/escola/418/cardapios/1')
        assert res.status_code == 200

    def test_get_cardapios_por_data(self, client):
        res = client.get('/cardapios/20180622')
        assert res.status_code == 200
