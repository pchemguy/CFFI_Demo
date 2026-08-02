PRAGMA foreign_keys = 0;

DROP TABLE IF EXISTS attributes;
DROP TABLE IF EXISTS kinds;

CREATE TABLE kinds (
    "id"   INTEGER PRIMARY KEY,
    "name" TEXT COLLATE NOCASE NOT NULL UNIQUE
);

CREATE TABLE attributes (
    "id" INTEGER PRIMARY KEY,
    "name"      TEXT COLLATE NOCASE NOT NULL UNIQUE,
    "cname"     TEXT COLLATE NOCASE NOT NULL,
    "kind"      TEXT COLLATE NOCASE NOT NULL,
    "item"      TEXT COLLATE NOCASE,
    "length"    INTEGER,
    "fields"    TEXT COLLATE NOCASE,
    "args"      TEXT COLLATE NOCASE,
    "result"    TEXT COLLATE NOCASE,
    "ellipsis"  TEXT COLLATE NOCASE,
    "abi"       TEXT COLLATE NOCASE,
    "elements"  TEXT COLLATE NOCASE,
    "relements" TEXT COLLATE NOCASE,
    CONSTRAINT "fk_attributes_kind_kinds_name"
        FOREIGN KEY ("kind") REFERENCES "kinds"("name")
);

INSERT INTO kinds(id, name) VALUES
    (0, 'primitive'),
    (1, 'pointer'),
    (2, 'array'),
    (3, 'function'),
    (4, 'struct'),
    (5, 'union'),
    (6, 'enum');

PRAGMA foreign_keys = 1;
