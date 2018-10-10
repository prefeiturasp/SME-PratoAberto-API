FROM mongo

COPY db_dump/*.bson /db_dump/
COPY db_dump/*.json /db_dump/

CMD mongorestore --host db:27017 --drop -d pratoaberto --nsInclude 'pratoaberto.*s' /db_dump/
