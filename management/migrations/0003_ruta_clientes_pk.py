from django.db import migrations

REBUILD_SQL = """
PRAGMA foreign_keys = OFF;

CREATE TABLE ruta_clientes_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ruta INTEGER NOT NULL,
    nit_cliente TEXT NOT NULL,
    orden_visita INTEGER NOT NULL,
    id_tiempo_cliente INTEGER NOT NULL DEFAULT 1,
    hora_inicio TEXT,
    hora_fin TEXT,
    resultado_visita TEXT NOT NULL DEFAULT 'PENDIENTE',
    observaciones TEXT,
    FOREIGN KEY (id_ruta) REFERENCES rutas(id_ruta) ON DELETE CASCADE,
    FOREIGN KEY (nit_cliente) REFERENCES clientes(nit),
    FOREIGN KEY (resultado_visita) REFERENCES cat_resultado_visita(resultado_visita),
    FOREIGN KEY (id_tiempo_cliente) REFERENCES cat_tiempo_cliente(id_tiempo_cliente)
);

INSERT INTO ruta_clientes_new (
    id_ruta,
    nit_cliente,
    orden_visita,
    id_tiempo_cliente,
    hora_inicio,
    hora_fin,
    resultado_visita,
    observaciones
)
SELECT
    id_ruta,
    nit_cliente,
    orden_visita,
    id_tiempo_cliente,
    hora_inicio,
    hora_fin,
    resultado_visita,
    observaciones
FROM ruta_clientes;

DROP TABLE ruta_clientes;
ALTER TABLE ruta_clientes_new RENAME TO ruta_clientes;

CREATE UNIQUE INDEX IF NOT EXISTS UQ_rc_ruta_cliente ON ruta_clientes(id_ruta, nit_cliente);
CREATE INDEX IF NOT EXISTS IX_rc_ruta_orden ON ruta_clientes(id_ruta, orden_visita);
CREATE INDEX IF NOT EXISTS IX_rc_cliente ON ruta_clientes(nit_cliente);

PRAGMA foreign_keys = ON;
"""


def rebuild_ruta_clientes(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return

    cursor = schema_editor.connection.cursor()
    columns = cursor.execute("PRAGMA table_info('ruta_clientes')").fetchall()
    if any(col[1] == 'id' for col in columns):
        return

    raw_conn = schema_editor.connection.connection
    raw_conn.executescript(REBUILD_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ('management', '0002_historial_tables'),
    ]

    operations = [
        migrations.RunPython(rebuild_ruta_clientes, migrations.RunPython.noop),
    ]
