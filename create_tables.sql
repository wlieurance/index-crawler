-- Text encoding used: UTF-8
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

DROP TABLE IF EXISTS dnd_monsters;
CREATE TABLE dnd_monsters (name TEXT, pubkey TEXT, category TEXT, npc_name TEXT, size TEXT, type TEXT, tags TEXT, alignment TEXT, envrionment TEXT, challenge REAL, xp INTEGER, page INTEGER, srd BOOLEAN, description TEXT, PRIMARY KEY(name, pubkey));

DROP TABLE IF EXISTS dnd_spells;
CREATE TABLE dnd_spells (name TEXT PRIMARY KEY, level TEXT, school TEXT, classes TEXT, subclasses TEXT, ritual BOOLEAN, concentration BOOLEAN);

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
