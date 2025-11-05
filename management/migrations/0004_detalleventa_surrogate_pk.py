from django.db import migrations

REBUILD_SQL = """
PRAGMA foreign_keys = OFF;

CREATE TABLE detalle_venta_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    linea INTEGER NOT NULL,
    codigo_producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC NOT NULL,
    FOREIGN KEY (id_venta) REFERENCES ventas(id_venta) ON DELETE CASCADE,
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);

INSERT INTO detalle_venta_new (
    id_venta,
    linea,
    codigo_producto,
    cantidad,
    precio_unitario
)
SELECT
    id_venta,
    linea,
    codigo_producto,
    cantidad,
    precio_unitario
FROM detalle_venta;

DROP TABLE detalle_venta;
ALTER TABLE detalle_venta_new RENAME TO detalle_venta;

CREATE UNIQUE INDEX IF NOT EXISTS UQ_dv_venta_linea ON detalle_venta(id_venta, linea);
CREATE INDEX IF NOT EXISTS IX_dv_venta ON detalle_venta(id_venta);

PRAGMA foreign_keys = ON;
"""


def add_surrogate_pk(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return

    cursor = schema_editor.connection.cursor()
    columns = cursor.execute("PRAGMA table_info('detalle_venta')").fetchall()
    if any(col[1] == 'id' for col in columns):
        return

    schema_editor.connection.connection.executescript(REBUILD_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ('management', '0003_ruta_clientes_pk'),
    ]

    operations = [
        migrations.RunPython(add_surrogate_pk, migrations.RunPython.noop),
    ]
