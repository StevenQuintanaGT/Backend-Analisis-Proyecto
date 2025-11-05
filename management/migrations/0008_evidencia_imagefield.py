from django.db import migrations


def migrate_evidencias_table(apps, schema_editor):
    connection = schema_editor.connection
    cursor = connection.cursor()

    if connection.vendor == "sqlite":
        cursor.execute("PRAGMA foreign_keys=OFF;")
        cursor.execute("ALTER TABLE evidencias_fotograficas RENAME TO evidencias_fotograficas_old;")
        cursor.execute(
            """
            CREATE TABLE evidencias_fotograficas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imagen TEXT,
                url TEXT,
                descripcion TEXT,
                nit_cliente TEXT,
                id_ruta INTEGER,
                id_venta INTEGER,
                registrada_en TEXT,
                FOREIGN KEY (nit_cliente) REFERENCES clientes(nit),
                FOREIGN KEY (id_ruta) REFERENCES rutas(id_ruta),
                FOREIGN KEY (id_venta) REFERENCES ventas(id_venta)
            )
            """
        )
        cursor.execute(
            "INSERT INTO evidencias_fotograficas (id, url, descripcion, nit_cliente, id_ruta, id_venta, registrada_en) "
            "SELECT id, url, descripcion, nit_cliente, id_ruta, id_venta, registrada_en FROM evidencias_fotograficas_old"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS IX_evidencias_cliente ON evidencias_fotograficas(nit_cliente);")
        cursor.execute("CREATE INDEX IF NOT EXISTS IX_evidencias_ruta ON evidencias_fotograficas(id_ruta);")
        cursor.execute("CREATE INDEX IF NOT EXISTS IX_evidencias_venta ON evidencias_fotograficas(id_venta);")
        cursor.execute("DROP TABLE evidencias_fotograficas_old;")
        cursor.execute("PRAGMA foreign_keys=ON;")
    else:
        cursor.execute(
            "IF COL_LENGTH('sistema.evidencias_fotograficas', 'imagen') IS NULL "
            "ALTER TABLE sistema.evidencias_fotograficas ADD imagen NVARCHAR(260) NULL"
        )
        cursor.execute(
            "ALTER TABLE sistema.evidencias_fotograficas ALTER COLUMN url NVARCHAR(1024) NULL"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0007_expand_evidencia_url"),
    ]

    operations = [
        migrations.RunPython(migrate_evidencias_table, migrations.RunPython.noop),
    ]
