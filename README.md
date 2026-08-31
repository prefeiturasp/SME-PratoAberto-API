# Estratégia de Transformação Digital e Governo Aberto na SME

Como um governo pode atuar para garantir o bem comum de todos? Na SME, acreditamos que um dos meios para isso seja garantir transparência e prestação de contas e constante relação entre governo e sociedade para o desenvolvimento e implementação de políticas públicas. 

A Portaria SME nº 8.008, de 12 de novembro de 2018 oficializou a estratégia da Secretaria Municipal de Educação de SP para que nossas ações sejam pautadas nos princípios de Governo Aberto e para usarmos os valores e benefícios do mundo digital para melhorarmos nossos processos e serviços para os cidadãos. 
Com isso, pretendemos: 
- aumentar os níveis de transparência ativa e de abertura de dados, garantindo a proteção de dados pessoais; 
- instituir metodologias ágeis e colaborativas como parte do processo de desenvolvimento e de evolução de sistemas administrativos e de serviços digitais; 
- fortalecer o controle das políticas educacionais e da aplicação de recursos por parte da gestão e da sociedade; 
- promover espaços e metodologias de colaboração entre governo, academia, sociedade civil e setor privado. 

O [Ateliê do Software](http://forum.govit.prefeitura.sp.gov.br/uploads/default/original/1X/c88a4715eb3f9fc3ceb882c1f6afe9e308805a17.pdf) é uma das ferramentas para operacionalização. Baseado em um modelo de contratação inspirado pelos movimentos ágil e de Software Craftsmanship, trabalhamos com equipes multidisciplinares para o desenvolvimento de produtos que beneficiam toda a comunidade escolar (técnicos da SME e DREs, gestores, professores, alunos e famílias) e concretizam os objetivos da Estratégia de Transformação Digital e Governo Aberto “Pátio Digital”.

# Conteúdo

 1. [Sobre o Produto](#Sobre-o-Produto)
 5. [Comunicação](#Comunicação)
 6. [Como contribuir](#como-contribuir)
 7. [Repositórios](#Repositórios)
 8. [Instalação e Configuração](#Instalação-e-Configuração)
 
# Sobre o Produto

## Visão de Futuro

Para a **comunidade e servidores da Secretaria Municipal de Educação (SME)**  

Que  **necessitam de informações sobre as refeições servidas nas Unidades Educacionais (UE) da Rede Municipal de Educação de São Paulo**  

O **Prato Aberto**  

É uma **plataforma web**  

Que  **divulga os cardápios semanais de alimentação**  

Diferentemente do **antigo processo**  

O nosso produto **garante acesso facilitado para toda a população ter acesso às informações.**

## Objetivo do Negócio

O Prato Aberto é uma plataforma que garante a transparência das refeições servidas nas Unidades Educacionais da Rede Municipal de Educação de São Paulo. A ferramenta permite a consulta dos cardápios por dia e por escola, com visualização no mapa. Além de facilitar a consulta dos cardápios,a plataforma permite a avaliação da qualidade das refeições e prevê interação com usuários via Facebook e Telegram, por meio de um assistente virtual, o Robô Edu.

## Personas

### Comunidade

**- Características principais:** familiares e responsáveis, jornalistas e pesquisadores que desejam ter mais informações sobre as refeições servidas
**- Necessidades:** ter acesso simplificado às refeições servidas de determinada UE

### Unidades Educacionais

**- Características principais:** diretores e equipe da UE que trabalham para ofertar a alimentação para crianças e adolescentes
**- Necessidades:** precisam ter visibilidade das refeições futuras

### SME

**- Características principais:** profissionais da DINUTRE que precisam publicizar os cardápios criados
**- Necessidades:** ferramenta que facilite a divulgação dos cardápios por UE

## Funcionalidades

- Mapa com geolocalização para busca de UE
- Visualização de cardápio por UE
- Chatbot via Facebook e Telegram

# Comunicação

| Canal de comunicação | Objetivos |
|----------------------|-----------|
| [Issues do Github](https://github.com/prefeiturasp/SME-PratoAberto-Frontend/issues) | - Sugestão de novas funcionalidades<br> - Reportar bugs<br> - Discussões técnicas |

# Como contribuir

Contribuições são **super bem vindas**! Se você tem vontade de construir o Prato Aberto conosco, veja o nosso [guia de contribuição](./CONTRIBUTING.md) onde explicamos detalhadamente como trabalhamos e de que formas você pode nos ajudar a alcançar nossos objetivos. Lembrando que todos devem seguir  nosso [código de conduta](./CODEOFCONDUCT.md).

# Repositórios

1. [Robô Edu](https://github.com/prefeiturasp/SME-PratoAberto-Edu)
2. [API](https://github.com/prefeiturasp/SME-PratoAberto-API)
3. [Editor](https://github.com/prefeiturasp/SME-PratoAberto-Editor)

# Instalação e Configuração

Instale os requisitos através do `requirements.txt` e configure uma variável de ambiente chamada API_MONGO_URI com o apontamento para a base.

```
pip install -r requirements.txt
export API_MONGO_URI=localhost:27017
FLASK_APP=api.py flask run
```

## Instalação usando Docker

Dentro do diretório do projeto, inicie a aplicação usando `docker-compose`.

`docker-compose up -D --build`


Instale MongoDB versão mínima 3.6:

[Windows](http://treehouse.github.io/installation-guides/windows/mongo-windows.html)
[Mac](http://treehouse.github.io/installation-guides/mac/mongo-mac.html)

```
mongod --fork --logpath <arquivo_para_logs (exemplo:/var/log/mongod.log)>
mongorestore -d pratoaberto -c cardapios ./cardapios.bson 
mongorestore -d pratoaberto -c escolas ./escolas.bson 
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

## /status

Verifica se a API está online.


Retorno:

```
{
    "status": "ativo"
}
```

Baseado no Readme do [i-educar](https://github.com/portabilis/i-educar)
