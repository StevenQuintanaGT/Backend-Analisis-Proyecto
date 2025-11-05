-- =========================================================
-- DATABASE: AppWeb_Ruteros
-- NORMALIZACIÓN: 3FN (Tercera Forma Normal)
-- DBMS: SQL Server 2019+
-- =========================================================

IF DB_ID('AppWeb_Ruteros') IS NULL
    CREATE DATABASE AppWeb_Ruteros;
GO

USE AppWeb_Ruteros;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'sistema')
    EXEC('CREATE SCHEMA sistema');
GO

-- =========================================================
-- NIVEL 1: CATÁLOGOS (Atomicidad y Reusabilidad)
-- =========================================================

CREATE TABLE sistema.cat_estatus_credito (
    estatus_credito VARCHAR(2) NOT NULL PRIMARY KEY,
    descripcion NVARCHAR(100) NULL
);
INSERT INTO sistema.cat_estatus_credito VALUES 
    ('A+', 'Excelente'),
    ('A', 'Muy Bueno'),
    ('B', 'Bueno'),
    ('C', 'Regular');
GO

CREATE TABLE sistema.cat_presentacion (
    presentacion VARCHAR(15) NOT NULL PRIMARY KEY,
    descripcion NVARCHAR(100) NULL
);
INSERT INTO sistema.cat_presentacion VALUES 
    ('DOCENA', 'Presentación por docena'),
    ('INDIVIDUAL', 'Presentación individual');
GO

CREATE TABLE sistema.cat_resultado_visita (
    resultado_visita VARCHAR(20) NOT NULL PRIMARY KEY,
    descripcion NVARCHAR(100) NULL
);
INSERT INTO sistema.cat_resultado_visita VALUES 
    ('VENTA', 'Venta concretada'),
    ('NO_CONCRETADA', 'Sin venta'),
    ('PENDIENTE', 'Pendiente de resultado');
GO

CREATE TABLE sistema.cat_tiempo_cliente (
    id_tiempo_cliente TINYINT NOT NULL PRIMARY KEY,
    minutos INT NOT NULL CHECK (minutos IN (60, 120)),
    descripcion NVARCHAR(50) NOT NULL
);
INSERT INTO sistema.cat_tiempo_cliente VALUES 
    (1, 60, '1 hora'),
    (2, 120, '2 horas');
GO

CREATE TABLE sistema.cat_periodo (
    id_periodo TINYINT NOT NULL PRIMARY KEY,
    descripcion NVARCHAR(50) NOT NULL
);
INSERT INTO sistema.cat_periodo VALUES 
    (1, 'Diario'),
    (2, 'Semanal'),
    (3, 'Mensual'),
    (4, 'Trimestral');
GO

CREATE TABLE sistema.cat_estado_usuario (
    estado_usuario VARCHAR(20) NOT NULL PRIMARY KEY,
    descripcion NVARCHAR(100) NULL
);
INSERT INTO sistema.cat_estado_usuario VALUES 
    ('ACTIVO', 'Usuario activo'),
    ('INACTIVO', 'Usuario inactivo'),
    ('SUSPENDIDO', 'Usuario suspendido');
GO

CREATE TABLE sistema.cat_rol (
    rol VARCHAR(40) NOT NULL PRIMARY KEY,
    descripcion NVARCHAR(200) NULL
);
INSERT INTO sistema.cat_rol VALUES 
    ('ADMIN', 'Administrador del sistema');
GO

-- =========================================================
-- NIVEL 2: ENTIDADES PRINCIPALES (Sin dependencias)
-- =========================================================

CREATE TABLE sistema.clientes (
    nit CHAR(9) NOT NULL PRIMARY KEY,
    nombre NVARCHAR(150) NOT NULL,
    direccion NVARCHAR(250) NULL,
    correo_electronico NVARCHAR(150) NULL,
    estatus_credito VARCHAR(2) NOT NULL DEFAULT 'B',
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT CK_clientes_nit_digitos CHECK (nit NOT LIKE '%[^0-9]%'),
    CONSTRAINT FK_clientes_estatus FOREIGN KEY (estatus_credito)
        REFERENCES sistema.cat_estatus_credito(estatus_credito)
);

CREATE UNIQUE INDEX UQ_clientes_correo_notnull
    ON sistema.clientes(correo_electronico)
    WHERE correo_electronico IS NOT NULL;

CREATE INDEX IX_clientes_estatus ON sistema.clientes(estatus_credito);
GO

CREATE TABLE sistema.productos (
    codigo VARCHAR(30) NOT NULL PRIMARY KEY,
    descripcion NVARCHAR(200) NOT NULL,
    color NVARCHAR(50) NULL,
    precio_unitario DECIMAL(12,2) NOT NULL,
    presentacion VARCHAR(15) NOT NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT CK_productos_precio CHECK (precio_unitario >= 0),
    CONSTRAINT FK_productos_presentacion FOREIGN KEY (presentacion)
        REFERENCES sistema.cat_presentacion(presentacion)
);

CREATE INDEX IX_productos_presentacion ON sistema.productos(presentacion);
GO

CREATE TABLE sistema.vendedores (
    dpi CHAR(13) NOT NULL PRIMARY KEY,
    nombre NVARCHAR(150) NOT NULL,
    correo_electronico NVARCHAR(150) NULL,
    telefono NVARCHAR(30) NULL,
    sueldo DECIMAL(12,2) NOT NULL,
    nivel_exito TINYINT NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT CK_vendedores_dpi_digitos CHECK (dpi NOT LIKE '%[^0-9]%'),
    CONSTRAINT CK_vendedores_sueldo CHECK (sueldo >= 0),
    CONSTRAINT CK_vendedores_nivel_exito CHECK (nivel_exito BETWEEN 0 AND 100)
);

CREATE UNIQUE INDEX UQ_vendedores_correo_notnull
    ON sistema.vendedores(correo_electronico)
    WHERE correo_electronico IS NOT NULL;
GO

CREATE TABLE sistema.administradores (
    dpi CHAR(13) NOT NULL PRIMARY KEY,
    nombre NVARCHAR(150) NOT NULL,
    correo_electronico NVARCHAR(150) NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT CK_admin_dpi_digitos CHECK (dpi NOT LIKE '%[^0-9]%')
);

CREATE UNIQUE INDEX UQ_admin_correo_notnull
    ON sistema.administradores(correo_electronico)
    WHERE correo_electronico IS NOT NULL;
GO

-- =========================================================
-- NIVEL 3: SEGURIDAD (Normalización de Usuarios)
-- =========================================================

CREATE TABLE sistema.usuarios (
    id_usuario INT IDENTITY(1,1) PRIMARY KEY,
    usuario NVARCHAR(80) NOT NULL UNIQUE,
    contrasena_hash VARBINARY(64) NOT NULL,
    contrasena_salt VARBINARY(32) NOT NULL UNIQUE,
    ultimo_ingreso DATETIME2(3) NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE INDEX IX_usuarios_usuario ON sistema.usuarios(usuario);
GO

-- Relación 1:1 Administrador-Usuario
ALTER TABLE sistema.administradores
ADD id_usuario INT NULL UNIQUE,
    CONSTRAINT FK_admin_usuario FOREIGN KEY (id_usuario) 
        REFERENCES sistema.usuarios(id_usuario);
GO

CREATE TABLE sistema.usuarios_estados (
    id_usuario_estado INT IDENTITY(1,1) PRIMARY KEY,
    id_usuario INT NOT NULL,
    estado_usuario VARCHAR(20) NOT NULL,
    fecha_inicio DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    fecha_fin DATETIME2(3) NULL,
    observaciones NVARCHAR(250) NULL,
    
    CONSTRAINT FK_ue_usuario FOREIGN KEY (id_usuario) 
        REFERENCES sistema.usuarios(id_usuario) ON DELETE CASCADE,
    CONSTRAINT FK_ue_estado FOREIGN KEY (estado_usuario) 
        REFERENCES sistema.cat_estado_usuario(estado_usuario)
);

CREATE UNIQUE INDEX UX_ue_vigente 
    ON sistema.usuarios_estados(id_usuario) 
    WHERE fecha_fin IS NULL;

CREATE INDEX IX_ue_usuario_fechas 
    ON sistema.usuarios_estados(id_usuario, fecha_inicio, fecha_fin);
GO

CREATE TABLE sistema.usuarios_roles (
    id_usuario INT NOT NULL,
    rol VARCHAR(40) NOT NULL,
    asignado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT PK_usuarios_roles PRIMARY KEY (id_usuario, rol),
    CONSTRAINT FK_ur_usuario FOREIGN KEY (id_usuario) 
        REFERENCES sistema.usuarios(id_usuario) ON DELETE CASCADE,
    CONSTRAINT FK_ur_rol FOREIGN KEY (rol) 
        REFERENCES sistema.cat_rol(rol)
);
GO

-- =========================================================
-- NIVEL 4: RUTAS Y PLANIFICACIÓN
-- =========================================================

CREATE TABLE sistema.rutas (
    id_ruta INT IDENTITY(1,1) PRIMARY KEY,
    dpi_vendedor CHAR(13) NOT NULL,
    fecha DATE NOT NULL,
    nombre NVARCHAR(150) NULL,
    kilometros_estimados DECIMAL(8,2) NULL,
    tiempo_planificado_min INT NULL,
    tiempo_real_min INT NULL,
    resultado_global NVARCHAR(50) NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT FK_rutas_vendedor FOREIGN KEY (dpi_vendedor)
        REFERENCES sistema.vendedores(dpi),
    CONSTRAINT CK_rutas_fecha CHECK (fecha <= CAST(GETDATE() AS DATE))
);

CREATE INDEX IX_rutas_fecha_vendedor 
    ON sistema.rutas(fecha, dpi_vendedor);

CREATE INDEX IX_rutas_vendedor 
    ON sistema.rutas(dpi_vendedor);
GO

CREATE TABLE sistema.ruta_clientes (
    id_ruta INT NOT NULL,
    nit_cliente CHAR(9) NOT NULL,
    orden_visita INT NOT NULL,
    id_tiempo_cliente TINYINT NOT NULL DEFAULT 1,
    hora_inicio DATETIME2(3) NULL,
    hora_fin DATETIME2(3) NULL,
    resultado_visita VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    observaciones NVARCHAR(500) NULL,
    
    CONSTRAINT PK_ruta_clientes PRIMARY KEY (id_ruta, nit_cliente),
    CONSTRAINT CK_rc_orden_visita CHECK (orden_visita > 0),
    CONSTRAINT FK_rc_ruta FOREIGN KEY (id_ruta) 
        REFERENCES sistema.rutas(id_ruta) ON DELETE CASCADE,
    CONSTRAINT FK_rc_cliente FOREIGN KEY (nit_cliente) 
        REFERENCES sistema.clientes(nit),
    CONSTRAINT FK_rc_resultado FOREIGN KEY (resultado_visita)
        REFERENCES sistema.cat_resultado_visita(resultado_visita),
    CONSTRAINT FK_rc_tiempo_cliente FOREIGN KEY (id_tiempo_cliente)
        REFERENCES sistema.cat_tiempo_cliente(id_tiempo_cliente),
    CONSTRAINT CK_rc_horas CHECK (hora_fin IS NULL OR hora_inicio IS NULL OR hora_inicio <= hora_fin)
);

CREATE INDEX IX_rc_ruta_orden 
    ON sistema.ruta_clientes(id_ruta, orden_visita);

CREATE INDEX IX_rc_cliente 
    ON sistema.ruta_clientes(nit_cliente);

CREATE INDEX IX_rc_resultado 
    ON sistema.ruta_clientes(resultado_visita);
GO

-- =========================================================
-- NIVEL 5: METAS (Separada de Vendedor para 3FN)
-- =========================================================

CREATE TABLE sistema.metas_vendedor (
    id_meta INT IDENTITY(1,1) PRIMARY KEY,
    dpi_vendedor CHAR(13) NOT NULL,
    id_periodo TINYINT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    monto_meta DECIMAL(14,2) NOT NULL,
    monto_logrado DECIMAL(14,2) NOT NULL DEFAULT 0,
    peso_conversion TINYINT NOT NULL DEFAULT 60,
    peso_monto TINYINT NOT NULL DEFAULT 40,
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVA',
    observaciones NVARCHAR(500) NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT FK_mv_vendedor FOREIGN KEY (dpi_vendedor)
        REFERENCES sistema.vendedores(dpi),
    CONSTRAINT FK_mv_periodo FOREIGN KEY (id_periodo)
        REFERENCES sistema.cat_periodo(id_periodo),
    CONSTRAINT CK_mv_monto CHECK (monto_meta > 0 AND monto_logrado >= 0),
    CONSTRAINT CK_mv_fechas CHECK (fecha_inicio <= fecha_fin),
    CONSTRAINT CK_mv_pesos CHECK (peso_conversion + peso_monto = 100),
    CONSTRAINT CK_mv_estado CHECK (estado IN ('ACTIVA', 'PAUSADA', 'CERRADA')),
    CONSTRAINT CK_mv_pesos_range CHECK (peso_conversion BETWEEN 0 AND 100 AND peso_monto BETWEEN 0 AND 100)
);

CREATE INDEX IX_mv_vendedor_fecha 
    ON sistema.metas_vendedor(dpi_vendedor, fecha_inicio, fecha_fin);

CREATE INDEX IX_mv_estado 
    ON sistema.metas_vendedor(estado);
GO

-- =========================================================
-- NIVEL 6: TRANSACCIONES COMERCIALES
-- =========================================================

CREATE TABLE sistema.ventas (
    id_venta INT IDENTITY(1,1) PRIMARY KEY,
    fecha DATETIME2(3) NOT NULL,
    nit_cliente CHAR(9) NOT NULL,
    id_ruta INT NULL,
    total DECIMAL(14,2) NOT NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT CK_ventas_total CHECK (total >= 0),
    CONSTRAINT FK_ventas_cliente FOREIGN KEY (nit_cliente)
        REFERENCES sistema.clientes(nit),
    CONSTRAINT FK_ventas_ruta FOREIGN KEY (id_ruta)
        REFERENCES sistema.rutas(id_ruta)
);

CREATE INDEX IX_ventas_nit_fecha 
    ON sistema.ventas(nit_cliente, fecha);

CREATE INDEX IX_ventas_fecha 
    ON sistema.ventas(fecha);

CREATE INDEX IX_ventas_ruta 
    ON sistema.ventas(id_ruta);
GO

CREATE TABLE sistema.detalle_venta (
    id_venta INT NOT NULL,
    linea INT NOT NULL,
    codigo_producto VARCHAR(30) NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(12,2) NOT NULL,
    
    CONSTRAINT PK_detalle_venta PRIMARY KEY (id_venta, linea),
    CONSTRAINT CK_dv_cantidad CHECK (cantidad > 0),
    CONSTRAINT CK_dv_precio CHECK (precio_unitario >= 0),
    CONSTRAINT FK_dv_venta FOREIGN KEY (id_venta)
        REFERENCES sistema.ventas(id_venta) ON DELETE CASCADE,
    CONSTRAINT FK_dv_producto FOREIGN KEY (codigo_producto)
        REFERENCES sistema.productos(codigo) ON DELETE SET NULL
);

CREATE INDEX IX_dv_venta 
    ON sistema.detalle_venta(id_venta);

CREATE INDEX IX_dv_producto 
    ON sistema.detalle_venta(codigo_producto);
GO

CREATE TABLE sistema.cobros (
    id_cobro INT IDENTITY(1,1) PRIMARY KEY,
    nit_cliente CHAR(9) NOT NULL,
    id_venta INT NULL,
    fecha DATETIME2(3) NOT NULL,
    monto DECIMAL(14,2) NOT NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT CK_cobros_monto CHECK (monto > 0),
    CONSTRAINT FK_cobro_cliente FOREIGN KEY (nit_cliente)
        REFERENCES sistema.clientes(nit),
    CONSTRAINT FK_cobro_venta FOREIGN KEY (id_venta)
        REFERENCES sistema.ventas(id_venta)
);

CREATE INDEX IX_cobro_nit_fecha 
    ON sistema.cobros(nit_cliente, fecha);

CREATE INDEX IX_cobro_venta 
    ON sistema.cobros(id_venta);
GO

-- =========================================================
-- NIVEL 7: HISTORIAL (Snapshot normalizado)
-- =========================================================

CREATE TABLE sistema.historial_ventas (
    id_historial_venta BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_venta INT NOT NULL UNIQUE,
    id_ruta INT NULL,
    nit_cliente CHAR(9) NOT NULL,
    dpi_vendedor CHAR(13) NOT NULL,
    
    fecha_venta DATETIME2(3) NOT NULL,
    total_venta DECIMAL(14,2) NOT NULL,
    
    orden_visita INT NULL,
    resultado_visita VARCHAR(20) NULL,
    observaciones_visita NVARCHAR(500) NULL,
    
    kilometros_estimados DECIMAL(8,2) NULL,
    tiempo_planificado_total_min INT NULL,
    tiempo_cliente_asignado_min INT NULL,
    
    hora_inicio_visita DATETIME2(3) NULL,
    hora_fin_visita DATETIME2(3) NULL,
    tiempo_real_visita_min INT NULL,
    tiempo_real_ruta_min INT NULL,
    
    registrado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    actualizado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT FK_hv_venta FOREIGN KEY (id_venta)
        REFERENCES sistema.ventas(id_venta),
    CONSTRAINT FK_hv_ruta FOREIGN KEY (id_ruta)
        REFERENCES sistema.rutas(id_ruta),
    CONSTRAINT FK_hv_cliente FOREIGN KEY (nit_cliente)
        REFERENCES sistema.clientes(nit),
    CONSTRAINT FK_hv_vendedor FOREIGN KEY (dpi_vendedor)
        REFERENCES sistema.vendedores(dpi)
);

CREATE INDEX IX_hv_venta 
    ON sistema.historial_ventas(id_venta);

CREATE INDEX IX_hv_ruta 
    ON sistema.historial_ventas(id_ruta);

CREATE INDEX IX_hv_cliente 
    ON sistema.historial_ventas(nit_cliente);

CREATE INDEX IX_hv_vendedor 
    ON sistema.historial_ventas(dpi_vendedor);

CREATE INDEX IX_hv_fecha 
    ON sistema.historial_ventas(fecha_venta);
GO

CREATE TABLE sistema.historial_detalle_venta (
    id_historial_detalle BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_historial_venta BIGINT NOT NULL,
    linea INT NOT NULL,
    codigo_producto VARCHAR(30) NOT NULL,
    descripcion_producto NVARCHAR(200) NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(12,2) NOT NULL,
    subtotal DECIMAL(14,2) NOT NULL,
    registrado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT PK_hdv PRIMARY KEY (id_historial_venta, linea),
    CONSTRAINT CK_hdv_cantidad CHECK (cantidad > 0),
    CONSTRAINT CK_hdv_precio CHECK (precio_unitario >= 0 AND subtotal >= 0),
    CONSTRAINT FK_hdv_historial FOREIGN KEY (id_historial_venta)
        REFERENCES sistema.historial_ventas(id_historial_venta) ON DELETE CASCADE,
    CONSTRAINT FK_hdv_producto FOREIGN KEY (codigo_producto)
        REFERENCES sistema.productos(codigo)
);

CREATE INDEX IX_hdv_historial 
    ON sistema.historial_detalle_venta(id_historial_venta);
GO

CREATE TABLE sistema.evidencias_fotograficas (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    imagen NVARCHAR(260) NULL,
    url NVARCHAR(1024) NULL,
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
GO

-- =========================================================
-- NIVEL 8: AUDITORÍA
-- =========================================================

CREATE TABLE sistema.auditoria (
    id_auditoria BIGINT IDENTITY(1,1) PRIMARY KEY,
    fecha DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    id_usuario INT NULL,
    accion VARCHAR(20) NOT NULL,
    tabla_afectada NVARCHAR(128) NULL,
    clave_afectada NVARCHAR(128) NULL,
    antes_json NVARCHAR(MAX) NULL,
    despues_json NVARCHAR(MAX) NULL,
    ip_origen NVARCHAR(64) NULL,
    
    CONSTRAINT CK_auditoria_accion CHECK (accion IN ('CREAR','ACTUALIZAR','ELIMINAR','LOGIN','EXPORTAR','IMPORTAR','REPORTE')),
    CONSTRAINT FK_aud_usuario FOREIGN KEY (id_usuario)
        REFERENCES sistema.usuarios(id_usuario)
);

CREATE INDEX IX_aud_fecha_accion 
    ON sistema.auditoria(fecha, accion);

CREATE INDEX IX_aud_usuario 
    ON sistema.auditoria(id_usuario);

CREATE INDEX IX_aud_tabla 
    ON sistema.auditoria(tabla_afectada);
GO

-- =========================================================
-- NIVEL 9: IMPORTACIÓN
-- =========================================================

CREATE TABLE sistema.lotes_importacion (
    id_lote INT IDENTITY(1,1) PRIMARY KEY,
    nombre_archivo NVARCHAR(260) NOT NULL,
    hash_archivo VARBINARY(32) NULL,
    estado VARCHAR(15) NOT NULL,
    subido_por INT NOT NULL,
    subido_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    comentarios NVARCHAR(500) NULL,
    
    CONSTRAINT CK_li_estado CHECK (estado IN ('PENDIENTE','VALIDADO','CARGADO')),
    CONSTRAINT FK_li_usuario FOREIGN KEY (subido_por)
        REFERENCES sistema.usuarios(id_usuario)
);

CREATE INDEX IX_li_estado_fecha 
    ON sistema.lotes_importacion(estado, subido_en);

CREATE UNIQUE INDEX UX_li_hash 
    ON sistema.lotes_importacion(hash_archivo) 
    WHERE hash_archivo IS NOT NULL;
GO

CREATE TABLE sistema.items_importacion (
    id_item INT IDENTITY(1,1) PRIMARY KEY,
    id_lote INT NOT NULL,
    fila INT NOT NULL,
    datos_json NVARCHAR(MAX) NOT NULL,
    valido BIT NOT NULL,
    errores_json NVARCHAR(MAX) NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    
    CONSTRAINT CK_ii_fila CHECK (fila > 0),
    CONSTRAINT FK_ii_lote FOREIGN KEY (id_lote)
        REFERENCES sistema.lotes_importacion(id_lote) ON DELETE CASCADE
);

CREATE INDEX IX_ii_lote_fila 
    ON sistema.items_importacion(id_lote, fila);

CREATE INDEX IX_ii_valido 
    ON sistema.items_importacion(valido);
GO

CREATE TABLE sistema.archivos (
    id_archivo INT IDENTITY(1,1) PRIMARY KEY,
    tipo_entidad NVARCHAR(64) NOT NULL,
    id_entidad NVARCHAR(64) NOT NULL,
    categoria NVARCHAR(50) NULL,
    nombre_archivo NVARCHAR(260) NOT NULL,
    tipo_mime NVARCHAR(100) NULL,
    url NVARCHAR(1000) NOT NULL,
    tamano_bytes BIGINT NULL,
    creado_en DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE INDEX IX_archivos_entidad 
    ON sistema.archivos(tipo_entidad, id_entidad);
GO

-- =========================================================
-- TRIGGERS: Integridad y Auditoría
-- =========================================================

-- Auditoría para vendedores (RF-31: Cambio de salarios)
CREATE TRIGGER trg_auditoria_vendedores
ON sistema.vendedores
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, antes_json, despues_json)
    SELECT 'ACTUALIZAR', 'sistema.vendedores', i.dpi,
           (SELECT * FROM deleted d WHERE d.dpi = i.dpi FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
           (SELECT * FROM inserted i2 WHERE i2.dpi = i.dpi FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i
    INNER JOIN deleted d ON i.dpi = d.dpi;
END;
GO

-- Auditoría para clientes (RF-31: Gestión de estatus)
CREATE TRIGGER trg_auditoria_clientes
ON sistema.clientes
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, antes_json, despues_json)
    SELECT 'ACTUALIZAR', 'sistema.clientes', i.nit,
           (SELECT * FROM deleted d WHERE d.nit = i.nit FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
           (SELECT * FROM inserted i2 WHERE i2.nit = i.nit FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i
    INNER JOIN deleted d ON i.nit = d.nit;
END;
GO

-- Auditoría para rutas (RF-31: Cambio de rutas)
CREATE TRIGGER trg_auditoria_rutas
ON sistema.rutas
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- INSERT
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, despues_json)
    SELECT 'CREAR', 'sistema.rutas', CAST(i.id_ruta AS NVARCHAR),
           (SELECT * FROM inserted i2 WHERE i2.id_ruta = i.id_ruta FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i
    WHERE NOT EXISTS (SELECT 1 FROM deleted d WHERE d.id_ruta = i.id_ruta);
    
    -- UPDATE
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, antes_json, despues_json)
    SELECT 'ACTUALIZAR', 'sistema.rutas', CAST(i.id_ruta AS NVARCHAR),
           (SELECT * FROM deleted d WHERE d.id_ruta = i.id_ruta FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
           (SELECT * FROM inserted i2 WHERE i2.id_ruta = i.id_ruta FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i
    INNER JOIN deleted d ON i.id_ruta = d.id_ruta;
    
    -- DELETE
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, antes_json)
    SELECT 'ELIMINAR', 'sistema.rutas', CAST(d.id_ruta AS NVARCHAR),
           (SELECT * FROM deleted d2 WHERE d2.id_ruta = d.id_ruta FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM deleted d
    WHERE NOT EXISTS (SELECT 1 FROM inserted i WHERE i.id_ruta = d.id_ruta);
END;
GO

-- Actualizar timestamp en rutas
CREATE TRIGGER trg_ruta_clientes_timestamp
ON sistema.ruta_clientes
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE r
    SET actualizado_en = SYSUTCDATETIME()
    FROM sistema.rutas r
    WHERE r.id_ruta IN (
        SELECT id_ruta FROM inserted 
        UNION 
        SELECT id_ruta FROM deleted
    );
END;
GO

-- Recalcular tiempo_planificado_min
CREATE TRIGGER trg_calcular_tiempo_ruta
ON sistema.ruta_clientes
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE r
    SET tiempo_planificado_min = 
        ISNULL((r.kilometros_estimados / 60.0) * 90, 0) +
        ISNULL((
            SELECT SUM(ctc.minutos)
            FROM sistema.ruta_clientes rc
            INNER JOIN sistema.cat_tiempo_cliente ctc 
                ON rc.id_tiempo_cliente = ctc.id_tiempo_cliente
            WHERE rc.id_ruta = r.id_ruta
        ), 0),
        actualizado_en = SYSUTCDATETIME()
    FROM sistema.rutas r
    WHERE r.id_ruta IN (
        SELECT id_ruta FROM inserted 
        UNION 
        SELECT id_ruta FROM deleted
    );
END;
GO

-- Auditoría ruta_clientes
CREATE TRIGGER trg_auditoria_ruta_clientes
ON sistema.ruta_clientes
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- INSERT
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, despues_json)
    SELECT 'CREAR', 'sistema.ruta_clientes', 
           CAST(i.id_ruta AS NVARCHAR) + '-' + i.nit_cliente,
           (SELECT * FROM inserted i2 WHERE i2.id_ruta = i.id_ruta 
            AND i2.nit_cliente = i.nit_cliente FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i
    WHERE NOT EXISTS (SELECT 1 FROM deleted d WHERE d.id_ruta = i.id_ruta 
                      AND d.nit_cliente = i.nit_cliente);
    
    -- UPDATE
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, antes_json, despues_json)
    SELECT 'ACTUALIZAR', 'sistema.ruta_clientes', 
           CAST(i.id_ruta AS NVARCHAR) + '-' + i.nit_cliente,
           (SELECT * FROM deleted d WHERE d.id_ruta = i.id_ruta 
            AND d.nit_cliente = i.nit_cliente FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
           (SELECT * FROM inserted i2 WHERE i2.id_ruta = i.id_ruta 
            AND i2.nit_cliente = i.nit_cliente FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i
    INNER JOIN deleted d ON i.id_ruta = d.id_ruta AND i.nit_cliente = d.nit_cliente;
    
    -- DELETE
    INSERT INTO sistema.auditoria (accion, tabla_afectada, clave_afectada, antes_json)
    SELECT 'ELIMINAR', 'sistema.ruta_clientes', 
           CAST(d.id_ruta AS NVARCHAR) + '-' + d.nit_cliente,
           (SELECT * FROM deleted d2 WHERE d2.id_ruta = d.id_ruta 
            AND d2.nit_cliente = d.nit_cliente FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM deleted d
    WHERE NOT EXISTS (SELECT 1 FROM inserted i WHERE i.id_ruta = d.id_ruta 
                      AND i.nit_cliente = d.nit_cliente);
END;
GO