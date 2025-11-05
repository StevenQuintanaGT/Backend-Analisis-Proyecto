# Generated manually to allow DetalleVenta to mantener registros cuando se elimina un producto.
from django.db import migrations


SQLITE_FORWARD = """
PRAGMA foreign_keys = OFF;

CREATE TABLE detalle_venta__tmp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    linea INTEGER NOT NULL,
    codigo_producto TEXT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC NOT NULL,
    FOREIGN KEY (id_venta) REFERENCES ventas(id_venta) ON DELETE CASCADE,
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo) ON DELETE SET NULL
);

INSERT INTO detalle_venta__tmp (
    id,
    id_venta,
    linea,
    codigo_producto,
    cantidad,
    precio_unitario
)
SELECT
    id,
    id_venta,
    linea,
    codigo_producto,
    cantidad,
    precio_unitario
FROM detalle_venta;

DROP TABLE detalle_venta;
ALTER TABLE detalle_venta__tmp RENAME TO detalle_venta;

CREATE UNIQUE INDEX IF NOT EXISTS UQ_dv_venta_linea ON detalle_venta(id_venta, linea);
CREATE INDEX IF NOT EXISTS IX_dv_venta ON detalle_venta(id_venta);

PRAGMA foreign_keys = ON;
"""


SQLITE_BACKWARD = """
PRAGMA foreign_keys = OFF;

CREATE TABLE detalle_venta__tmp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    linea INTEGER NOT NULL,
    codigo_producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC NOT NULL,
    FOREIGN KEY (id_venta) REFERENCES ventas(id_venta) ON DELETE CASCADE,
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);

INSERT INTO detalle_venta__tmp (
    id,
    id_venta,
    linea,
    codigo_producto,
    cantidad,
    precio_unitario
)
SELECT
    id,
    id_venta,
    linea,
    codigo_producto,
    cantidad,
    precio_unitario
FROM detalle_venta;

DROP TABLE detalle_venta;
ALTER TABLE detalle_venta__tmp RENAME TO detalle_venta;

CREATE UNIQUE INDEX IF NOT EXISTS UQ_dv_venta_linea ON detalle_venta(id_venta, linea);
CREATE INDEX IF NOT EXISTS IX_dv_venta ON detalle_venta(id_venta);

PRAGMA foreign_keys = ON;
"""


SQLSERVER_FORWARD = """
DECLARE @constraint_name NVARCHAR(255);
SELECT @constraint_name = fk.name
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
JOIN sys.tables t ON fk.parent_object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.columns c ON fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id
WHERE s.name = 'sistema'
  AND t.name = 'detalle_venta'
  AND c.name = 'codigo_producto';

IF @constraint_name IS NOT NULL
    EXEC('ALTER TABLE sistema.detalle_venta DROP CONSTRAINT ' + QUOTENAME(@constraint_name));

ALTER TABLE sistema.detalle_venta ALTER COLUMN codigo_producto NVARCHAR(30) NULL;

ALTER TABLE sistema.detalle_venta WITH CHECK
ADD CONSTRAINT FK_detalle_venta_producto FOREIGN KEY (codigo_producto)
REFERENCES sistema.productos(codigo)
ON DELETE SET NULL;
"""


SQLSERVER_BACKWARD = """
IF EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE name = 'FK_detalle_venta_producto'
      AND parent_object_id = OBJECT_ID('sistema.detalle_venta')
)
    ALTER TABLE sistema.detalle_venta DROP CONSTRAINT FK_detalle_venta_producto;

ALTER TABLE sistema.detalle_venta ALTER COLUMN codigo_producto NVARCHAR(30) NOT NULL;

ALTER TABLE sistema.detalle_venta WITH CHECK
ADD CONSTRAINT FK_detalle_venta_producto FOREIGN KEY (codigo_producto)
REFERENCES sistema.productos(codigo);
"""


def forwards(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "sqlite":
        connection.connection.executescript(SQLITE_FORWARD)
    else:
        cursor = connection.cursor()
        cursor.execute(SQLSERVER_FORWARD)


def backwards(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "sqlite":
        connection.connection.executescript(SQLITE_BACKWARD)
    else:
        cursor = connection.cursor()
        cursor.execute(SQLSERVER_BACKWARD)


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0008_evidencia_imagefield"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(forwards, backwards),
            ],
            state_operations=[],
        ),
    ]
