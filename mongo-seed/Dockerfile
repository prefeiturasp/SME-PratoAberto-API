FROM mongo

COPY db_dump/cardapios.bson /db_dump/cardapios.bson
COPY db_dump/escolas.bson /db_dump/escolas.bson

CMD mongorestore --host db:27017 --drop -d pratoaberto --nsInclude 'pratoaberto.*s' /db_dump/
