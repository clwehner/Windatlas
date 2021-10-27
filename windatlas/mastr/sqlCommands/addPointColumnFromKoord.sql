ALTER TABLE mastr_raw."EinheitenWind"
  DROP COLUMN IF EXISTS geo_point;

ALTER TABLE mastr_raw."EinheitenWind"
  ADD COLUMN geo_point POINT;

UPDATE mastr_raw."EinheitenWind"
  SET geo_point = point("Laengengrad", "Breitengrad");

/*Creat Points for one table without PostGIS
ALTER TABLE mastr_raw."EinheitenWind"
  DROP COLUMN IF EXISTS geo_point;

ALTER TABLE mastr_raw."EinheitenWind"
  ADD COLUMN geo_point POINT;

UPDATE mastr_raw."EinheitenWind"
  SET geo_point = point("Laengengrad", "Breitengrad");
*/

/*Same with PostGIS installed

ALTER TABLE mastr_raw."EinheitenWind"
  ADD COLUMN geo_point GEOGRAPHY(POINT,4326);

UPDATE mastr_raw."EinheitenWind"
  SET geo_point = 'SRID=4326;POINT(' || "Laengengrad" || ' ' || "Breitengrad" || ')';

*/

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
$$
DECLARE
    rec record;
BEGIN
    FOR rec IN 
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns 
        WHERE column_name = "Laengengrad"
    LOOP
        EXECUTE format('ALTER TABLE %I.%I DROP COLUMN IF EXISTS geo_point;',
            rec.table_schema, rec.table_name);
        EXECUTE format('ALTER TABLE %I.%I ADD COLUMN COLUMN geo_point POINT;',
            rec.table_schema, rec.table_name);
        EXECUTE format('UPDATE %I.%I SET geo_point = point("Laengengrad", "Breitengrad");',
            rec.table_schema, rec.table_name);
    END LOOP;
END;
$$
LANGUAGE plpgsql;

*/