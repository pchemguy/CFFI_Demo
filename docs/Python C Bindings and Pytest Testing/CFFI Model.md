## 📗 CFFI CTypes Attributes  SQLite

> [!NOTE] Prompt
> 
> I need a Python script which will open/create SQLite db "cffi_model.db". It should probably create a class for db. It will also provide a function "attributes_insert", which should take optional argument db/connection and use the one on the instance, if none provided; mandatory arg: a dict or an iterable of dicts each dict representing a new "attributes" row. If any value is an object, force it to a string.
> 
> "attributes" schema:
> ```sql
> CREATE TABLE attributes (
>     "id" INTEGER PRIMARY KEY,
>     "name"      TEXT COLLATE NOCASE NOT NULL UNIQUE,
>     "cname"     TEXT COLLATE NOCASE NOT NULL UNIQUE,
>     "kind"      TEXT COLLATE NOCASE NOT NULL,
>     "group"     TEXT COLLATE NOCASE NOT NULL,
>     "item"      TEXT COLLATE NOCASE,
>     "length"    INTEGER,
>     "fields"    TEXT COLLATE NOCASE,
>     "args"      TEXT COLLATE NOCASE,
>     "result"    TEXT COLLATE NOCASE,
>     "ellipsis"  TEXT COLLATE NOCASE,
>     "abi"       TEXT COLLATE NOCASE,
>     "elements"  TEXT COLLATE NOCASE,
>     "relements" TEXT COLLATE NOCASE,
>     CONSTRAINT "fk_attributes_kind_kinds_name"
>         FOREIGN KEY ("kind") REFERENCES "kinds"("name"),
>     CONSTRAINT "fk_attributes_group_groups_name"
>         FOREIGN KEY ("group") REFERENCES "groups"("name")
> );
> ```
> If db does not exist, use schema.sql next to the script.
