from django.db import migrations


def expand_url_column(apps, schema_editor):
    connection = schema_editor.connection
    cursor = connection.cursor()

    if connection.vendor == "sqlite":
        # URL column already stores TEXT in sqlite, no change required.
        return

    cursor.execute(
        """
        IF EXISTS (
            SELECT 1
            FROM sys.columns c
            JOIN sys.tables t ON t.object_id = c.object_id
            JOIN sys.schemas s ON s.schema_id = t.schema_id
            WHERE s.name = 'sistema' AND t.name = 'evidencias_fotograficas' AND c.name = 'url'
        )
        BEGIN
            ALTER TABLE sistema.evidencias_fotograficas ALTER COLUMN url NVARCHAR(1024) NOT NULL;
        END
        """
    )


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0006_evidenciafotografica"),
    ]

    operations = [
        migrations.RunPython(expand_url_column, migrations.RunPython.noop),
    ]
