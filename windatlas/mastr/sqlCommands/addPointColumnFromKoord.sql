--Creat Points for one table without PostGIS
ALTER TABLE mastr_raw."EinheitenWind"
  DROP COLUMN IF EXISTS geom;

ALTER TABLE mastr_raw."EinheitenWind"
  ADD COLUMN geom GEOMETRY(POINT, 4326);

UPDATE mastr_raw."EinheitenWind"
  SET geom = ST_SetSRID(ST_MakePoint("Laengengrad", "Breitengrad"), 4326);

/*Looping over all tables in a schema 

--Old Version
DECLARE
    rec record;
BEGIN
    FOR rec IN 
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns 
        WHERE column_name = 'x'
    LOOP
        EXECUTE format('ALTER TABLE %I.%I RENAME COLUMN %I TO newname;',
            rec.table_schema, rec.table_name, rec.column_name);
    END LOOP;
END;


--My Version
DO
$func$
DECLARE
    rec record;
BEGIN
    FOR formal_table IN
        SELECT quote_ident(table_name)
        FROM information_schema.tables 
        WHERE column_name = "Laengengrad"
    LOOP
        EXECUTE format('ALTER TABLE %I.%I DROP COLUMN IF EXISTS geom;',
            rec.table_schema, rec.table_name);
        EXECUTE format('ALTER TABLE %I.%I ADD COLUMN geom GEOMETRY(POINT, 4326);',
            rec.table_schema, rec.table_name);
        EXECUTE format('UPDATE %I.%I SET geom = ST_SetSRID(ST_MakePoint("Laengengrad", "Breitengrad"), 4326);',
            rec.table_schema, rec.table_name);
    END LOOP;
END;
$func$
LANGUAGE plpgsql;

*/