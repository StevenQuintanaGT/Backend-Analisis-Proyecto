from django.db import migrations


def create_evidencias_table(apps, schema_editor):
    connection = schema_editor.connection
    cursor = connection.cursor()

    if connection.vendor == "sqlite":
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evidencias_fotograficas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
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
            "CREATE INDEX IF NOT EXISTS IX_evidencias_cliente ON evidencias_fotograficas(nit_cliente)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS IX_evidencias_ruta ON evidencias_fotograficas(id_ruta)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS IX_evidencias_venta ON evidencias_fotograficas(id_venta)"
        )
    else:
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM sys.tables t
                JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE t.name = 'evidencias_fotograficas' AND s.name = 'sistema'
            )
            BEGIN
                CREATE TABLE sistema.evidencias_fotograficas (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    url NVARCHAR(500) NOT NULL,
                    descripcion NVARCHAR(300) NULL,
                    nit_cliente CHAR(9) NULL,
                    id_ruta INT NULL,
                    id_venta INT NULL,
                    registrada_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
                    CONSTRAINT FK_evidencias_cliente FOREIGN KEY (nit_cliente)
                        REFERENCES sistema.clientes(nit),
                    CONSTRAINT FK_evidencias_ruta FOREIGN KEY (id_ruta)
                        REFERENCES sistema.rutas(id_ruta),
                    CONSTRAINT FK_evidencias_venta FOREIGN KEY (id_venta)
                        REFERENCES sistema.ventas(id_venta)
                );

                CREATE INDEX IX_evidencias_cliente ON sistema.evidencias_fotograficas(nit_cliente);
                CREATE INDEX IX_evidencias_ruta ON sistema.evidencias_fotograficas(id_ruta);
                CREATE INDEX IX_evidencias_venta ON sistema.evidencias_fotograficas(id_venta);
            END
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0005_ruta_nombre"),
    ]

    operations = [
        migrations.RunPython(create_evidencias_table, migrations.RunPython.noop),
    ]
