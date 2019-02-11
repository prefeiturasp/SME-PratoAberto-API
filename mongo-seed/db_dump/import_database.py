#! /usr/bin/python3.6
# -*- coding=utf-8 -*-

import pandas as pad
from pymongo import MongoClient

FILE_EXCEL = 'EscolasDiretas e Mistas.xlsx'
HOST = 'localhost'
PORT = 27017
DBNM = 'pratoaberto'

""" Classe de importação e 
    atualização de dados na API
"""


class ImportDatabase(object):

    def __init__(self):
        self.client = None
        self.db = None
        self.excel_list = []
        self.collection_school = None

        self.__connect_mongodb()

        self.__read_file_excel(FILE_EXCEL)

        self.cod_eol = self.df['COD_EOL']
        self.gestao = self.df['GESTÃO']
        self.tipo_escola = self.df['ESCOLA']
        self.agrupamento = self.df['AGRUPAMENTO']
        self.escolas = self.df['NOME ESCOLA']
        self.endereco = self.df['ENDEREÇO']
        self.bairro = self.df['BAIRRO']
        self.latitude = self.df['LAT']
        self.longitude = self.df['LON']
        self.refeicoes = self.df['REFEIÇÕES']
        self.idades = self.df['IDADES']
        self.status = self.df['STATUS']
        self.edital = self.df['EDITAL']
        self.dre = self.df['DRE']

        self.__connect_mongodb()

    def __read_file_excel(self, filename):
        self.df = pad.read_excel(filename)

    def __to_dict_from_excel(self):
        for i in self.df.index:
            xlsx_dict = {}

            xlsx_dict['_id'] = int(self.cod_eol[i])
            xlsx_dict['nome'] = self.escolas[i]
            xlsx_dict['tipo_unidade'] = self.tipo_escola[i]
            xlsx_dict['tipo_atendimento'] = self.gestao[i]
            xlsx_dict['endereco'] = self.endereco[i]
            xlsx_dict['bairro'] = self.bairro[i]
            xlsx_dict['lat'] = ''
            xlsx_dict['lon'] = ''
            xlsx_dict['telefone'] = ''
            xlsx_dict['agrupamento_regiao'] = int(self.agrupamento[i])
            xlsx_dict['edital'] = ''
            xlsx_dict['agrupamento'] = ''
            xlsx_dict['status'] = self.status[i]
            xlsx_dict['idades'] = self.idades[i].split(',')
            xlsx_dict['refeicoes'] = self.refeicoes[i].split(',')
            xlsx_dict['dre'] = self.dre[i]

            self.excel_list.append(xlsx_dict)


""" Method to connect in mongodb """


def __connect_mongodb(self):
    self.client = MongoClient(HOST, PORT)
    self.db = self.client[DBNM]

    self.collection_school = self.db['escolas']


def insert_new(self, values):
    try:
        id = self.collection_school.insert_one(values).inserted_id
        return id
    except Exception as e:
        print(str(e))


def update_rows(self, value):
    try:
        return self.collection_school.update({"_id": int(value['_id'])}, {"$set": {'dre': str(value['dre'])}})
    except Exception as e:
        print("#### ERROR UPDATE ###")
        print(str(e))


def schools_exists(self):
    self.__to_dict_from_excel()
    exists = []
    for x in self.excel_list:
        if self.collection_school.find_one({'_id': x['_id']}):
            exists.append({'_id': x['_id'], 'dre': x['dre']})
    return exists


def schools_not_exists(self):
    self.__to_dict_from_excel()

    not_exists = []

    for x in self.excel_list:
        if not self.collection_school.find_one({"_id": x['_id']}):
            not_exists.append(x)

    return not_exists


def run_add(self):
    cont_add = 0
    for i in self.schools_not_exists():
        self.insert_new(i)
        cont_add += 1

    print("Total rows added {} successful")


def run_update(self):
    cont_up = 0
    for u in self.schools_exists():
        resp = self.update_rows(u)
        if resp['nModified'] == 1:
            cont_up += 1

    print("The total rows updated is {}".format(cont_up))


if __name__ == '__main__':
    robo = ImportDatabase()
    robo.run_add()
    robo.run_update()
