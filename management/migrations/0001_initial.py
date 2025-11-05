from django.db import migrations


SQL = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cat_estatus_credito (
    estatus_credito TEXT PRIMARY KEY,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS cat_presentacion (
    presentacion TEXT PRIMARY KEY,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS cat_resultado_visita (
    resultado_visita TEXT PRIMARY KEY,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS cat_tiempo_cliente (
    id_tiempo_cliente INTEGER PRIMARY KEY,
    minutos INTEGER NOT NULL,
    descripcion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clientes (
    nit TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    direccion TEXT,
    correo_electronico TEXT,
    estatus_credito TEXT NOT NULL DEFAULT 'B',
    creado_en TEXT,
    actualizado_en TEXT,
    FOREIGN KEY (estatus_credito) REFERENCES cat_estatus_credito(estatus_credito)
);

CREATE UNIQUE INDEX IF NOT EXISTS UQ_clientes_correo_notnull ON clientes(correo_electronico);
CREATE INDEX IF NOT EXISTS IX_clientes_estatus ON clientes(estatus_credito);

CREATE TABLE IF NOT EXISTS productos (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT NOT NULL,
    color TEXT,
    precio_unitario NUMERIC NOT NULL,
    presentacion TEXT NOT NULL,
    creado_en TEXT,
    actualizado_en TEXT,
    FOREIGN KEY (presentacion) REFERENCES cat_presentacion(presentacion)
);
CREATE INDEX IF NOT EXISTS IX_productos_presentacion ON productos(presentacion);

CREATE TABLE IF NOT EXISTS vendedores (
    dpi TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    correo_electronico TEXT,
    telefono TEXT,
    sueldo NUMERIC NOT NULL,
    nivel_exito INTEGER,
    creado_en TEXT,
    actualizado_en TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS UQ_vendedores_correo_notnull ON vendedores(correo_electronico);

CREATE TABLE IF NOT EXISTS rutas (
    id_ruta INTEGER PRIMARY KEY AUTOINCREMENT,
    dpi_vendedor TEXT NOT NULL,
    fecha TEXT NOT NULL,
    nombre TEXT,
    kilometros_estimados NUMERIC,
    tiempo_planificado_min INTEGER,
    tiempo_real_min INTEGER,
    resultado_global TEXT,
    creado_en TEXT,
    actualizado_en TEXT,
    FOREIGN KEY (dpi_vendedor) REFERENCES vendedores(dpi)
);
CREATE INDEX IF NOT EXISTS IX_rutas_fecha_vendedor ON rutas(fecha, dpi_vendedor);

CREATE TABLE IF NOT EXISTS ruta_clientes (
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
CREATE UNIQUE INDEX IF NOT EXISTS UQ_rc_ruta_cliente ON ruta_clientes(id_ruta, nit_cliente);
CREATE INDEX IF NOT EXISTS IX_rc_ruta_orden ON ruta_clientes(id_ruta, orden_visita);
CREATE INDEX IF NOT EXISTS IX_rc_cliente ON ruta_clientes(nit_cliente);

CREATE TABLE IF NOT EXISTS ventas (
    id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    nit_cliente TEXT NOT NULL,
    id_ruta INTEGER,
    total NUMERIC NOT NULL,
    creado_en TEXT,
    actualizado_en TEXT,
    FOREIGN KEY (nit_cliente) REFERENCES clientes(nit),
    FOREIGN KEY (id_ruta) REFERENCES rutas(id_ruta)
);
CREATE INDEX IF NOT EXISTS IX_ventas_nit_fecha ON ventas(nit_cliente, fecha);

CREATE TABLE IF NOT EXISTS detalle_venta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    linea INTEGER NOT NULL,
    codigo_producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC NOT NULL,
    FOREIGN KEY (id_venta) REFERENCES ventas(id_venta) ON DELETE CASCADE,
    FOREIGN KEY (codigo_producto) REFERENCES productos(codigo)
);
CREATE UNIQUE INDEX IF NOT EXISTS UQ_dv_venta_linea ON detalle_venta(id_venta, linea);
CREATE INDEX IF NOT EXISTS IX_dv_venta ON detalle_venta(id_venta);

-- Simple tables used by the app
CREATE TABLE IF NOT EXISTS management_registrovisita (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendedor_id TEXT,
    cliente_id TEXT,
    fecha TEXT,
    resultado TEXT,
    productos_entregados TEXT,
    evidencia_foto TEXT,
    notas TEXT,
    FOREIGN KEY (vendedor_id) REFERENCES vendedores(dpi),
    FOREIGN KEY (cliente_id) REFERENCES clientes(nit)
);

CREATE TABLE IF NOT EXISTS management_userprofile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    rol TEXT
);

CREATE TABLE IF NOT EXISTS management_reportfile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,
    nombre_archivo TEXT,
    file_path TEXT,
    fecha_generacion TEXT
);

-- Seed some catalog data
INSERT OR IGNORE INTO cat_estatus_credito(estatus_credito, descripcion) VALUES ('A+','Excelente'),('A','Muy Bueno'),('B','Bueno'),('C','Regular');
INSERT OR IGNORE INTO cat_presentacion(presentacion, descripcion) VALUES ('DOCENA','Presentación por docena'),('INDIVIDUAL','Presentación individual');
INSERT OR IGNORE INTO cat_resultado_visita(resultado_visita, descripcion) VALUES ('VENTA','Venta concretada'),('NO_CONCRETADA','Sin venta'),('PENDIENTE','Pendiente de resultado');
INSERT OR IGNORE INTO cat_tiempo_cliente(id_tiempo_cliente, minutos, descripcion) VALUES (1,60,'1 hora'),(2,120,'2 horas');

'''


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(SQL),
    ]
