[![Maintainability](https://api.codeclimate.com/v1/badges/a96e3bfb2024cd6464f7/maintainability)](https://codeclimate.com/github/prefeiturasp/SME-PratoAberto-API/maintainability)

# Pátio Digital

_“Recurso público retorna ao público”._

Nós somos o **pátio digital**, uma iniciativa da Secretaria Municipal de Educação de São Paulo que, por meio do fortalecimento da transparência, da participação social e do desenvolvimento de novas tecnologias, aproxima diferentes grupos da sociedade civil por um objetivo maior: a melhoria da educação na cidade de São Paulo.

# Prato Aberto

"Prato Aberto – Comida Boa Não Tem Segredo".

# API do Prato Aberto

A API serve dados sobre as escolas e as refeições das escolas da rede pública da cidade de São Paulo.

## Conteúdo

1. [Sobre o prato aberto](#sobre-o-prato-aberto)
2. [Comunicação](#comunicação)
3. [Roadmap de tecnologia](#roadmap-de-tecnologia)
4. [Como contribuir](#como-contribuir)
5. [Instalação](#instalação)

## Sobre o prato aberto

Projetada para funcionar em computadores e dispositivos móveis como tablets e celulares. A ferramenta permite a consulta dos cardápios por dia e por escola, com visualização no mapa. É a primeira vez que os cardápios
são divulgados por unidade escolar. Além de facilitar a consulta dos cardápios,a plataforma permite a avaliação da qualidade das refeições e prevê interação com usuários via Facebook e Telegram, por meio de um assistente virtual, o Robô Edu.

### Nossos outros repositórios

1. [Robô Edu](https://github.com/prefeiturasp/SME-PratoAberto-Edu)
2. [API](https://github.com/prefeiturasp/SME-PratoAberto-API)
3. [Editor](https://github.com/prefeiturasp/SME-PratoAberto-Editor)

## Comunicação

| Canal de comunicação | Objetivos |
|----------------------|-----------|
| [Issues do Github](https://github.com/prefeiturasp/SME-PratoAberto-Frontend/issues) | - Sugestão de novas funcionalidades<br> - Reportar bugs<br> - Discussões técnicas |
| [Telegram](https://t.me/patiodigital ) | - Comunicar novidades sobre os projetos<br> - Movimentar a comunidade<br>  - Falar tópicos que **não** demandem discussões profundas |

Qualquer outro grupo de discussão não é reconhecido oficialmente.

## Roadmap de tecnologia

### Passos iniciais
- Melhorar a qualidade de código
- Iniciar a escrita de testes unitários
- Configurar Docker
- Iniciar escrita de testes funcionais
- Melhorar documentação de maneira enxuta
- CI com jenkins

## Como contribuir

Contribuições são **super bem vindas**! Se você tem vontade de construir o
prato aberto conosco, veja o nosso [guia de contribuição](./CONTRIBUTING.md)
onde explicamos detalhadamente como trabalhamos e de que formas você pode nos
ajudar a alcançar nossos objetivos. Lembrando que todos devem seguir
nosso [código de conduta](./CODEOFCONDUCT.md).

## Instalação

Instale os requisitos através do `requirements.txt` e configure uma variável de ambiente chamada API_MONGO_URI com o apontamento para a base.

```
pip install -r requirements.txt
export API_MONGO_URI=localhost:27017
FLASK_APP=api.py flask run
```

# Endpoints

## /apidocs
Documentação dos Endpoints da API.

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

Baseado no Readme do [i-educar](https://github.com/portabilis/i-educar)
