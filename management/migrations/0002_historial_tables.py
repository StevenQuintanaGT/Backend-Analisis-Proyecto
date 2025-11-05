from django.db import migrations


SQL = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS historial_ventas (
    id_historial_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER UNIQUE,
    id_ruta INTEGER,
    nit_cliente TEXT,
    dpi_vendedor TEXT,
    fecha_venta TEXT,
    total_venta NUMERIC,
    orden_visita INTEGER,
    resultado_visita TEXT,
    observaciones_visita TEXT,
    kilometros_estimados NUMERIC,
    tiempo_planificado_total_min INTEGER,
    tiempo_cliente_asignado_min INTEGER,
    hora_inicio_visita TEXT,
    hora_fin_visita TEXT,
    tiempo_real_visita_min INTEGER,
    tiempo_real_ruta_min INTEGER,
    registrado_en TEXT,
    actualizado_en TEXT,
    FOREIGN KEY(id_ruta) REFERENCES rutas(id_ruta),
    FOREIGN KEY(nit_cliente) REFERENCES clientes(nit),
    FOREIGN KEY(dpi_vendedor) REFERENCES vendedores(dpi)
);

CREATE INDEX IF NOT EXISTS IX_historial_venta_ruta ON historial_ventas(id_ruta);
CREATE INDEX IF NOT EXISTS IX_historial_venta_cliente ON historial_ventas(nit_cliente);

CREATE TABLE IF NOT EXISTS historial_detalle_venta (
    id_historial_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_historial_venta INTEGER NOT NULL,
    linea INTEGER,
    codigo_producto TEXT,
    descripcion_producto TEXT,
    cantidad INTEGER,
    precio_unitario NUMERIC,
    subtotal NUMERIC,
    registrado_en TEXT,
    FOREIGN KEY(id_historial_venta) REFERENCES historial_ventas(id_historial_venta) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS IX_historial_detalle_historial ON historial_detalle_venta(id_historial_venta);
'''


class Migration(migrations.Migration):
    dependencies = [
        ('management', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(SQL),
    ]
