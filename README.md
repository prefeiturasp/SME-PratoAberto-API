[![Maintainability](https://api.codeclimate.com/v1/badges/a96e3bfb2024cd6464f7/maintainability)](https://codeclimate.com/github/prefeiturasp/SME-PratoAberto-API/maintainability)

# API

A API serve dados sobre as escolas e as refeições das escolas da rede pública da cidade de São Paulo.

## Instalação

Instale os requisitos através do `requirements.txt` e configure uma variável de ambiente chamada API_MONGO_URI com o apontamento para a base.

```
pip install -r requirements.txt
export API_MONGO_URI=localhost:27017
FLASK_APP=app.py flask run
```

# Endpoints

## /escolas

Lista escolas da rede publica.

Argumentos de query string:

```
nome:   string - opcional
        Permite a filtragem da lista de escolas pelo nome
```



Retorno:

```
[
    {
        "_id": 91065,
        "nome": "EMEI ELIS REGINA - (TERCEI.)",
        "endereco": "R. ERNESTO MANOGRASSO, 340",
        "bairro": "CID. SÃO MATEUS",
        "lat": -23.611117,
        "lon": -46.479426
    },
    ...
]
```

## /escola/<int:id_escola>

Lista detalhes de uma determina escola pelo seu identificador (código Escola Online - EOL)

Parametros:

```
id_escola:    int
```


Retorno:

```
{
    "nome": "EMEI ELIS REGINA - (TERCEI.)",
    "tipo_unidade": "EMEI",
    "tipo_atendimento": "TERCEIRIZADA",
    "agrupamento": 4,
    "endereco": "R. ERNESTO MANOGRASSO, 340",
    "bairro": "CID. SÃO MATEUS",
    "telefone": "(11)29199960",
    "lat": -23.611117,
    "lon": -46.479426,
    "idades": [
        "Z - UNIDADES SEM FAIXA"
    ]
}
```

## /cardapios ou /cardapios/<data>

Lista os cardapios disponíveis

Parametros:

```
data:   string - opcional
        Formato: YYYYMMDD
```

Argumentos de query string:

```
agrupamento:        string - opcional
tipo_atendimento:   string - opcional
tipo_unidade:       string - opcional
idade:              string - opcional
data_inicial:       string - opcional
data_final:         string - opcional
```


Retorno:

```
[
    {
        "data": "20170922",
        "idade": "1 A 3 MESES",
        "tipo_atendimento": "DIRETA",
        "tipo_unidade": "CEI_CONVENIADO",
        "agrupamento": "4",
        "cardapio": {
            "Jantar": [
                "FORMULA LÁCTEA"
            ],
            "Desjejum": [
                "FORMULA LACTEA"
            ],
            "Almoco": [
                "FORMULA LACTEA"
            ],
            "Lanche": [
                "FORMULA LÁCTEA"
            ]
        },
    },
    ...
]
```


## /editor/cardapios

Permite a listagem e a alteração dos dados de cardápio.

Para acesso, é necessário enviar uma chave através do cabeçalho HTTP `key`. A chave deve ser a mesma que a variável de ambiente `API_KEY`

Argumentos de query string:

```
status:             string - opcional
agrupamento:        string - opcional
tipo_atendimento:   string - opcional
tipo_unidade:       string - opcional
idade:              string - opcional
data_inicial:       string - opcional
data_final:         string - opcional
```


Retorno:

```
[
    {
        "data": "20170922",
        "idade": "1 A 3 MESES",
        "tipo_atendimento": "DIRETA",
        "tipo_unidade": "CEI_CONVENIADO",
        "agrupamento": "4",
        "cardapio": {
            "Jantar": [
                "FORMULA LÁCTEA"
            ],
            "Desjejum": [
                "FORMULA LACTEA"
            ],
            "Almoco": [
                "FORMULA LACTEA"
            ],
            "Lanche": [
                "FORMULA LÁCTEA"
            ]
        },
    },
    ...
]
```
