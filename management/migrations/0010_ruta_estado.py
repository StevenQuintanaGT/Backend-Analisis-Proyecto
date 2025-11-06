from django.db import migrations


SQL = """
ALTER TABLE rutas ADD COLUMN estado TEXT DEFAULT 'PENDIENTE';
"""


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0009_detalleventa_nullable'),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]
