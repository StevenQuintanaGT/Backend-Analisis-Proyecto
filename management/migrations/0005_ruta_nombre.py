from django.db import migrations


def add_nombre_column(apps, schema_editor):
    connection = schema_editor.connection
    cursor = connection.cursor()

    if connection.vendor == "sqlite":
        columns = cursor.execute("PRAGMA table_info('rutas')").fetchall()
        if any(col[1] == 'nombre' for col in columns):
            return
        cursor.execute("ALTER TABLE rutas ADD COLUMN nombre TEXT")
    else:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE name = 'nombre' AND object_id = OBJECT_ID('sistema.rutas')) "
            "ALTER TABLE sistema.rutas ADD nombre NVARCHAR(150) NULL"
        )


class Migration(migrations.Migration):
    dependencies = [
        ('management', '0004_detalleventa_surrogate_pk'),
    ]

    operations = [
        migrations.RunPython(add_nombre_column, migrations.RunPython.noop),
    ]
