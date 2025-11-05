-- =========================================================
-- STORED PROCEDURES: Lógica de Negocio Normalizada
-- =========================================================
USE AppWeb_Ruteros;
GO

-- =========================================================
-- SP: Crear Meta para Vendedor (RF-19)
-- =========================================================
CREATE PROCEDURE sistema.sp_crear_meta_vendedor
    @dpi_vendedor CHAR(13),
    @id_periodo TINYINT,
    @fecha_inicio DATE,
    @fecha_fin DATE,
    @monto_meta DECIMAL(14,2),
    @peso_conversion TINYINT = 60,
    @peso_monto TINYINT = 40,
    @observaciones NVARCHAR(500) = NULL,
    @id_meta INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        -- Validar pesos
        IF @peso_conversion + @peso_monto != 100
        BEGIN
            RAISERROR('Los pesos deben sumar 100. Conversión: %d, Monto: %d', 16, 1, @peso_conversion, @peso_monto);
            RETURN;
        END
        
        -- Validar vendedor
        IF NOT EXISTS (SELECT 1 FROM sistema.vendedores WHERE dpi = @dpi_vendedor)
        BEGIN
            RAISERROR('Vendedor no existe', 16, 1);
            RETURN;
        END
        
        -- Validar período
        IF NOT EXISTS (SELECT 1 FROM sistema.cat_periodo WHERE id_periodo = @id_periodo)
        BEGIN
            RAISERROR('Período no válido', 16, 1);
            RETURN;
        END
        
        -- Insertar meta
        INSERT INTO sistema.metas_vendedor (
            dpi_vendedor, id_periodo, fecha_inicio, fecha_fin, 
            monto_meta, peso_conversion, peso_monto, observaciones
        )
        VALUES (
            @dpi_vendedor, @id_periodo, @fecha_inicio, @fecha_fin,
            @monto_meta, @peso_conversion, @peso_monto, @observaciones
        );
        
        SET @id_meta = SCOPE_IDENTITY();
        
    END TRY
    BEGIN CATCH
        RAISERROR('Error al crear meta: %s', 16, 1, ERROR_MESSAGE());
    END CATCH
END;
GO

-- =========================================================
-- SP: Registrar Venta en Historial (RF-31)
-- =========================================================
CREATE PROCEDURE sistema.sp_registrar_venta_historial
    @id_venta INT,
    @id_ruta INT = NULL,
    @tiempo_real_visita_min INT = NULL,
    @id_historial_venta BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        DECLARE @nit_cliente CHAR(9),
                @dpi_vendedor CHAR(13),
                @fecha_venta DATETIME2(3),
                @total_venta DECIMAL(14,2);
        
        -- Obtener datos de venta
        SELECT @nit_cliente = nit_cliente,
               @fecha_venta = fecha,
               @total_venta = total,
               @id_ruta = ISNULL(@id_ruta, id_ruta)
        FROM sistema.ventas
        WHERE id_venta = @id_venta;
        
        IF @nit_cliente IS NULL
        BEGIN
            RAISERROR('Venta no existe', 16, 1);
            RETURN;
        END
        
        -- Obtener vendedor de la ruta
        IF @id_ruta IS NOT NULL
        BEGIN
            SELECT @dpi_vendedor = dpi_vendedor
            FROM sistema.rutas
            WHERE id_ruta = @id_ruta;
        END
        
        -- Insertar en historial
        INSERT INTO sistema.historial_ventas (
            id_venta, id_ruta, nit_cliente, dpi_vendedor,
            fecha_venta, total_venta,
            orden_visita, resultado_visita, observaciones_visita,
            kilometros_estimados, tiempo_planificado_total_min, 
            tiempo_cliente_asignado_min,
            hora_inicio_visita, hora_fin_visita, tiempo_real_visita_min,
            tiempo_real_ruta_min
        )
        SELECT
            v.id_venta,
            @id_ruta,
            v.nit_cliente,
            ISNULL(@dpi_vendedor, r.dpi_vendedor),
            v.fecha,
            v.total,
            rc.orden_visita,
            rc.resultado_visita,
            rc.observaciones,
            r.kilometros_estimados,
            r.tiempo_planificado_min,
            ctc.minutos,
            rc.hora_inicio,
            rc.hora_fin,
            @tiempo_real_visita_min,
            r.tiempo_real_min
        FROM sistema.ventas v
        LEFT JOIN sistema.rutas r ON @id_ruta = r.id_ruta
        LEFT JOIN sistema.ruta_clientes rc ON @id_ruta = rc.id_ruta 
            AND v.nit_cliente = rc.nit_cliente
        LEFT JOIN sistema.cat_tiempo_cliente ctc ON rc.id_tiempo_cliente = ctc.id_tiempo_cliente
        WHERE v.id_venta = @id_venta;
        
        SET @id_historial_venta = SCOPE_IDENTITY();
        
        -- Copiar detalles
        INSERT INTO sistema.historial_detalle_venta (
            id_historial_venta, linea, codigo_producto,
            descripcion_producto, cantidad, precio_unitario, subtotal
        )
        SELECT
            @id_historial_venta,
            dv.linea,
            dv.codigo_producto,
            p.descripcion,
            dv.cantidad,
            dv.precio_unitario,
            (dv.cantidad * dv.precio_unitario)
        FROM sistema.detalle_venta dv
        INNER JOIN sistema.productos p ON dv.codigo_producto = p.codigo
        WHERE dv.id_venta = @id_venta;
        
    END TRY
    BEGIN CATCH
        RAISERROR('Error al registrar venta en historial: %s', 16, 1, ERROR_MESSAGE());
    END CATCH
END;
GO

-- =========================================================
-- SP: Actualizar Monto Meta (Llamar tras venta)
-- =========================================================
CREATE PROCEDURE sistema.sp_actualizar_monto_meta
    @dpi_vendedor CHAR(13),
    @monto_venta DECIMAL(14,2),
    @nivel_exito_nuevo TINYINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        DECLARE @id_meta INT,
                @monto_meta DECIMAL(14,2),
                @monto_logrado DECIMAL(14,2),
                @peso_conversion TINYINT,
                @peso_monto TINYINT,
                @tasa_conversion DECIMAL(5,2),
                @porcentaje_monto DECIMAL(5,2);
        
        -- Obtener meta activa
        SELECT @id_meta = id_meta,
               @monto_meta = monto_meta,
               @monto_logrado = monto_logrado,
               @peso_conversion = peso_conversion,
               @peso_monto = peso_monto
        FROM sistema.metas_vendedor
        WHERE dpi_vendedor = @dpi_vendedor
          AND estado = 'ACTIVA'
          AND CAST(GETDATE() AS DATE) BETWEEN fecha_inicio AND fecha_fin;
        
        IF @id_meta IS NULL
        BEGIN
            RAISERROR('No hay meta activa para este vendedor', 16, 1);
            RETURN;
        END
        
        -- Actualizar monto logrado
        UPDATE sistema.metas_vendedor
        SET monto_logrado = monto_logrado + @monto_venta,
            actualizado_en = SYSUTCDATETIME()
        WHERE id_meta = @id_meta;
        
        -- Calcular tasa de conversión
        SELECT @tasa_conversion = 
            CAST(ROUND(
                (CAST(COUNT(CASE WHEN rc.resultado_visita = 'VENTA' THEN 1 END) AS FLOAT) 
                 / NULLIF(COUNT(*), 0)) * 100, 2
            ) AS DECIMAL(5,2))
        FROM sistema.rutas r
        INNER JOIN sistema.ruta_clientes rc ON r.id_ruta = rc.id_ruta
        WHERE r.dpi_vendedor = @dpi_vendedor;
        
        -- Calcular porcentaje monto
        SET @monto_logrado = @monto_logrado + @monto_venta;
        SET @porcentaje_monto = 
            CAST(ROUND(
                CASE 
                    WHEN @monto_meta = 0 THEN 100
                    ELSE (@monto_logrado * 100.0 / @monto_meta)
                END, 2
            ) AS DECIMAL(5,2));
        
        -- Calcular nivel de éxito
        SET @nivel_exito_nuevo = CAST(ROUND(
            (ISNULL(@tasa_conversion, 0) * @peso_conversion / 100) +
            (ISNULL(@porcentaje_monto, 0) * @peso_monto / 100), 2
        ) AS TINYINT);
        
        -- Limitar entre 0 y 100
        SET @nivel_exito_nuevo = CASE 
            WHEN @nivel_exito_nuevo > 100 THEN 100
            WHEN @nivel_exito_nuevo < 0 THEN 0
            ELSE @nivel_exito_nuevo
        END;
        
        -- Actualizar nivel_exito en vendedor
        UPDATE sistema.vendedores
        SET nivel_exito = @nivel_exito_nuevo,
            actualizado_en = SYSUTCDATETIME()
        WHERE dpi = @dpi_vendedor;
        
    END TRY
    BEGIN CATCH
        RAISERROR('Error al actualizar meta: %s', 16, 1, ERROR_MESSAGE());
    END CATCH
END;
GO

-- =========================================================
-- SP: Crear Ruta con Clientes (RF-15)
-- =========================================================
CREATE PROCEDURE sistema.sp_crear_ruta
    @dpi_vendedor CHAR(13),
    @fecha DATE,
    @kilometros_estimados DECIMAL(8,2),
    @id_ruta INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        -- Validar vendedor
        IF NOT EXISTS (SELECT 1 FROM sistema.vendedores WHERE dpi = @dpi_vendedor)
        BEGIN
            RAISERROR('Vendedor no existe', 16, 1);
            RETURN;
        END
        
        -- Insertar ruta
        INSERT INTO sistema.rutas (
            dpi_vendedor, fecha, kilometros_estimados
        )
        VALUES (
            @dpi_vendedor, @fecha, @kilometros_estimados
        );
        
        SET @id_ruta = SCOPE_IDENTITY();
        
    END TRY
    BEGIN CATCH
        RAISERROR('Error al crear ruta: %s', 16, 1, ERROR_MESSAGE());
    END CATCH
END;
GO

-- =========================================================
-- SP: Asignar Cliente a Ruta (RF-17)
-- =========================================================
CREATE PROCEDURE sistema.sp_asignar_cliente_ruta
    @id_ruta INT,
    @nit_cliente CHAR(9),
    @orden_visita INT,
    @id_tiempo_cliente TINYINT = 1
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        -- Validar ruta
        IF NOT EXISTS (SELECT 1 FROM sistema.rutas WHERE id_ruta = @id_ruta)
        BEGIN
            RAISERROR('Ruta no existe', 16, 1);
            RETURN;
        END
        
        -- Validar cliente
        IF NOT EXISTS (SELECT 1 FROM sistema.clientes WHERE nit = @nit_cliente)
        BEGIN
            RAISERROR('Cliente no existe', 16, 1);
            RETURN;
        END
        
        -- Validar tiempo cliente
        IF NOT EXISTS (SELECT 1 FROM sistema.cat_tiempo_cliente WHERE id_tiempo_cliente = @id_tiempo_cliente)
        BEGIN
            RAISERROR('Tiempo cliente no válido', 16, 1);
            RETURN;
        END
        
        -- Insertar asignación
        INSERT INTO sistema.ruta_clientes (
            id_ruta, nit_cliente, orden_visita, id_tiempo_cliente, resultado_visita
        )
        VALUES (
            @id_ruta, @nit_cliente, @orden_visita, @id_tiempo_cliente, 'PENDIENTE'
        );
        
        -- El trigger actualiza automáticamente tiempo_planificado_min
        
    END TRY
    BEGIN CATCH
        RAISERROR('Error al asignar cliente: %s', 16, 1, ERROR_MESSAGE());
    END CATCH
END;
GO

-- =========================================================
-- SP: Registrar Venta
-- =========================================================
CREATE PROCEDURE sistema.sp_registrar_venta
    @fecha DATETIME2(3),
    @nit_cliente CHAR(9),
    @id_ruta INT = NULL,
    @detalles_json NVARCHAR(MAX),
    @id_venta INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        DECLARE @total DECIMAL(14,2) = 0,
                @linea INT = 1;
        
        -- Validar cliente
        IF NOT EXISTS (SELECT 1 FROM sistema.clientes WHERE nit = @nit_cliente)
        BEGIN
            RAISERROR('Cliente no existe', 16, 1);
            RETURN;
        END
        
        -- Insertar venta
        INSERT INTO sistema.ventas (fecha, nit_cliente, id_ruta, total)
        VALUES (@fecha, @nit_cliente, @id_ruta, 0);
        
        SET @id_venta = SCOPE_IDENTITY();
        
        -- Insertar detalles desde JSON
        INSERT INTO sistema.detalle_venta (id_venta, linea, codigo_producto, cantidad, precio_unitario)
        SELECT 
            @id_venta,
            ROW_NUMBER() OVER (ORDER BY (SELECT 1)),
            JSON_VALUE(value, '$.codigo'),
            JSON_VALUE(value, '$.cantidad'),
            JSON_VALUE(value, '$.precio')
        FROM OPENJSON(@detalles_json) AS items;
        
        -- Actualizar total
        UPDATE sistema.ventas
        SET total = (
            SELECT SUM(cantidad * precio_unitario)
            FROM sistema.detalle_venta
            WHERE id_venta = @id_venta
        )
        WHERE id_venta = @id_venta;
        
        -- Registrar en historial
        DECLARE @id_historial BIGINT;
        EXEC sistema.sp_registrar_venta_historial 
            @id_venta = @id_venta,
            @id_ruta = @id_ruta,
            @id_historial_venta = @id_historial OUTPUT;
        
        -- Actualizar meta
        DECLARE @nivel_exito TINYINT;
        IF @id_ruta IS NOT NULL
        BEGIN
            DECLARE @dpi_vendedor CHAR(13);
            SELECT @dpi_vendedor = dpi_vendedor FROM sistema.rutas WHERE id_ruta = @id_ruta;
            
            EXEC sistema.sp_actualizar_monto_meta 
                @dpi_vendedor = @dpi_vendedor,
                @monto_venta = (SELECT total FROM sistema.ventas WHERE id_venta = @id_venta),
                @nivel_exito_nuevo = @nivel_exito OUTPUT;
        END
        
    END TRY
    BEGIN CATCH
        RAISERROR('Error al registrar venta: %s', 16, 1, ERROR_MESSAGE());
    END CATCH
END;
GO

-- =========================================================
-- VISTAS PARA REPORTES
-- =========================================================

-- Vista: Meta Actual por Vendedor
CREATE VIEW sistema.vw_meta_actual_vendedor
AS
SELECT 
    v.dpi,
    v.nombre,
    mv.id_meta,
    cp.descripcion AS periodo,
    mv.fecha_inicio,
    mv.fecha_fin,
    mv.monto_meta,
    mv.monto_logrado,
    CAST(ROUND((mv.monto_logrado * 100.0 / NULLIF(mv.monto_meta, 0)), 2) AS DECIMAL(5,2)) 
        AS porcentaje_cumplimiento,
    (mv.monto_meta - mv.monto_logrado) AS diferencia,
    mv.peso_conversion,
    mv.peso_monto,
    mv.estado,
    v.nivel_exito
FROM sistema.metas_vendedor mv
INNER JOIN sistema.vendedores v ON mv.dpi_vendedor = v.dpi
INNER JOIN sistema.cat_periodo cp ON mv.id_periodo = cp.id_periodo
WHERE mv.estado = 'ACTIVA';
GO

-- Vista: Nivel de Éxito Detallado
CREATE VIEW sistema.vw_nivel_exito_detallado
AS
SELECT 
    v.dpi,
    v.nombre,
    v.nivel_exito AS nivel_exito_actual,
    COUNT(rc.id_ruta) AS total_visitas,
    SUM(CASE WHEN rc.resultado_visita = 'VENTA' THEN 1 ELSE 0 END) AS visitas_venta,
    CAST(ROUND(
        (CAST(SUM(CASE WHEN rc.resultado_visita = 'VENTA' THEN 1 ELSE 0 END) AS FLOAT) 
         / NULLIF(COUNT(rc.id_ruta), 0)) * 100, 2
    ) AS DECIMAL(5,2)) AS tasa_conversion,
    SUM(ve.total) AS monto_total_vendido,
    ISNULL(mv.monto_meta, 0) AS monto_meta,
    ISNULL(mv.monto_logrado, 0) AS monto_logrado,
    mv.peso_conversion,
    mv.peso_monto
FROM sistema.vendedores v
LEFT JOIN sistema.rutas r ON v.dpi = r.dpi_vendedor
LEFT JOIN sistema.ruta_clientes rc ON r.id_ruta = rc.id_ruta
LEFT JOIN sistema.ventas ve ON r.id_ruta = ve.id_ruta 
    AND rc.nit_cliente = ve.nit_cliente
LEFT JOIN sistema.vw_meta_actual_vendedor mv ON v.dpi = mv.dpi
GROUP BY v.dpi, v.nombre, v.nivel_exito, mv.monto_meta, mv.monto_logrado, 
         mv.peso_conversion, mv.peso_monto;
GO

-- Vista: Historial Completo con Análisis
CREATE VIEW sistema.vw_historial_completo
AS
SELECT 
    hv.id_historial_venta,
    hv.id_venta,
    hv.nit_cliente,
    c.nombre AS cliente,
    hv.dpi_vendedor,
    v.nombre AS vendedor,
    hv.fecha_venta,
    hv.total_venta,
    hv.resultado_visita,
    hv.tiempo_planificado_total_min,
    hv.tiempo_real_visita_min,
    (hv.tiempo_real_visita_min - hv.tiempo_planificado_total_min) AS diferencia_tiempo_min,
    CAST(ROUND(
        ((hv.tiempo_real_visita_min - hv.tiempo_planificado_total_min) * 100.0 
         / NULLIF(hv.tiempo_planificado_total_min, 0)), 2
    ) AS DECIMAL(5,2)) AS porcentaje_variacion,
    hv.registrado_en
FROM sistema.historial_ventas hv
INNER JOIN sistema.clientes c ON hv.nit_cliente = c.nit
INNER JOIN sistema.vendedores v ON hv.dpi_vendedor = v.dpi;
GO

-- =========================================================
-- EJEMPLOS DE USO
-- =========================================================
/*
-- 1. Crear meta
DECLARE @id_meta INT;
EXEC sistema.sp_crear_meta_vendedor 
    @dpi_vendedor = '1234567890101',
    @id_periodo = 3,
    @fecha_inicio = '2025-10-01',
    @fecha_fin = '2025-10-31',
    @monto_meta = 10000,
    @peso_conversion = 60,
    @peso_monto = 40,
    @id_meta = @id_meta OUTPUT;

-- 2. Crear ruta
DECLARE @id_ruta INT;
EXEC sistema.sp_crear_ruta 
    @dpi_vendedor = '1234567890101',
    @fecha = '2025-10-01',
    @kilometros_estimados = 45.5,
    @id_ruta = @id_ruta OUTPUT;

-- 3. Asignar clientes
EXEC sistema.sp_asignar_cliente_ruta 
    @id_ruta = @id_ruta,
    @nit_cliente = '123456789',
    @orden_visita = 1,
    @id_tiempo_cliente = 2;  -- 2 horas

-- 4. Registrar venta
DECLARE @id_venta INT;
EXEC sistema.sp_registrar_venta 
    @fecha = GETDATE(),
    @nit_cliente = '123456789',
    @id_ruta = @id_ruta,
    @detalles_json = '[{"codigo":"PROD001","cantidad":10,"precio":25.50}]',
    @id_venta = @id_venta OUTPUT;

-- 5. Consultar nivel de éxito
SELECT * FROM sistema.vw_nivel_exito_detallado
WHERE dpi = '1234567890101';
*/