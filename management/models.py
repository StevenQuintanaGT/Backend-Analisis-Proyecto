from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator, RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings

# Pequeña ayuda para que el mismo código funcione igual con SQLite y con SQL Server.
def _is_sqlite():
    try:
        engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        return engine == 'django.db.backends.sqlite3'
    except Exception:
        return False

_SQLITE = _is_sqlite()

def db_table(name: str) -> str:
    return name if _SQLITE else f'sistema.{name}'


# Catálogos básicos que existen en la base de datos de producción.
class CatEstatusCredito(models.Model):
    estatus_credito = models.CharField(max_length=2, primary_key=True)
    descripcion = models.CharField(max_length=100, null=True)

    class Meta:
        db_table = db_table('cat_estatus_credito')
        managed = _SQLITE


class CatPresentacion(models.Model):
    presentacion = models.CharField(max_length=15, primary_key=True)
    descripcion = models.CharField(max_length=100, null=True)

    class Meta:
        db_table = db_table('cat_presentacion')
        managed = _SQLITE


class CatResultadoVisita(models.Model):
    resultado_visita = models.CharField(max_length=20, primary_key=True)
    descripcion = models.CharField(max_length=100, null=True)

    class Meta:
        db_table = db_table('cat_resultado_visita')
        managed = _SQLITE


class CatTiempoCliente(models.Model):
    id_tiempo_cliente = models.PositiveSmallIntegerField(primary_key=True)
    minutos = models.IntegerField()
    descripcion = models.CharField(max_length=50)

    class Meta:
        db_table = db_table('cat_tiempo_cliente')
        managed = _SQLITE


# Información principal de clientes del sistema.
class Cliente(models.Model):
    nit = models.CharField(max_length=9, primary_key=True, validators=[RegexValidator(r'^\d+$', 'Sólo dígitos')])
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=250, blank=True, null=True)
    correo_electronico = models.CharField(max_length=150, blank=True, null=True, validators=[EmailValidator()])
    estatus_credito = models.CharField(max_length=2, default='B')
    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('clientes')
        managed = _SQLITE

    def __str__(self):
        return f"{self.nit} - {self.nombre}"


# Catálogo de productos que ofrecemos y su presentación.
class Producto(models.Model):
    codigo = models.CharField(max_length=30, primary_key=True)
    descripcion = models.CharField(max_length=200)
    color = models.CharField(max_length=50, blank=True, null=True)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    presentacion = models.ForeignKey(CatPresentacion, to_field='presentacion', db_column='presentacion', on_delete=models.PROTECT)
    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('productos')
        managed = _SQLITE

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


# Datos del equipo de ventas y su desempeño.
class Vendedor(models.Model):
    dpi = models.CharField(max_length=13, primary_key=True, validators=[RegexValidator(r'^\d+$', 'Sólo dígitos')])
    nombre = models.CharField(max_length=150)
    correo_electronico = models.CharField(max_length=150, blank=True, null=True, validators=[EmailValidator()])
    telefono = models.CharField(max_length=30, blank=True, null=True)
    sueldo = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    # nivel_exito en la BD es TINYINT 0..100; exponemos como porcentaje y derivamos alto/medio/bajo en serializer
    nivel_exito_porcent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        db_column='nivel_exito',
    )
    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('vendedores')
        managed = _SQLITE

    def save(self, *args, **kwargs):
        # Limpiamos el nombre para evitar espacios extra antes de guardar.
        self.nombre = self.nombre.strip()
        if len(self.nombre) > 150:
            raise ValueError('Nombre de vendedor excede 150 caracteres')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.dpi} - {self.nombre}"


# Planificación de rutas y visitas programadas.
class Ruta(models.Model):
    id_ruta = models.AutoField(primary_key=True)
    dpi_vendedor = models.ForeignKey(Vendedor, to_field='dpi', db_column='dpi_vendedor', on_delete=models.PROTECT)
    fecha = models.DateField()
    nombre = models.CharField(max_length=150, null=True, blank=True)
    kilometros_estimados = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tiempo_planificado_min = models.IntegerField(null=True, blank=True)
    tiempo_real_min = models.IntegerField(null=True, blank=True)
    resultado_global = models.CharField(max_length=50, null=True, blank=True)
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En proceso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('rutas')
        managed = _SQLITE

    def __str__(self):
        label = self.nombre or f"Ruta {self.id_ruta}"
        return f"{label} - {self.dpi_vendedor} - {self.fecha}"


# Relación entre clientes y rutas, con el orden de visita.
class ClienteRuta(models.Model):
    ruta = models.ForeignKey(Ruta, db_column='id_ruta', on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, db_column='nit_cliente', on_delete=models.CASCADE)
    orden_visita = models.PositiveIntegerField()
    id_tiempo_cliente = models.ForeignKey(CatTiempoCliente, db_column='id_tiempo_cliente', on_delete=models.PROTECT)
    hora_inicio = models.DateTimeField(null=True, blank=True)
    hora_fin = models.DateTimeField(null=True, blank=True)
    resultado_visita = models.ForeignKey(CatResultadoVisita, db_column='resultado_visita', on_delete=models.PROTECT, default='PENDIENTE')
    observaciones = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = db_table('ruta_clientes')
        managed = _SQLITE
        unique_together = (('ruta', 'cliente'),)
        ordering = ['orden_visita']

    def __str__(self):
        return f"{self.ruta.id_ruta} - {self.cliente.nit} - {self.orden_visita}"


# Cabecera de las ventas registradas en el sistema.
class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True)
    fecha = models.DateTimeField()
    nit_cliente = models.ForeignKey(Cliente, db_column='nit_cliente', to_field='nit', on_delete=models.PROTECT)
    id_ruta = models.ForeignKey(Ruta, db_column='id_ruta', null=True, blank=True, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    creado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('ventas')
        managed = _SQLITE

    def __str__(self):
        return f"Venta {self.id_venta} - {self.nit_cliente} - {self.fecha}"


# Detalle de productos vendidos dentro de cada venta.
class DetalleVenta(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_venta = models.ForeignKey(Venta, db_column='id_venta', on_delete=models.CASCADE)
    linea = models.IntegerField()
    codigo_producto = models.ForeignKey(
        Producto,
        db_column='codigo_producto',
        to_field='codigo',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = db_table('detalle_venta')
        managed = _SQLITE
        unique_together = (('id_venta', 'linea'),)

    def __str__(self):
        return f"Venta {self.id_venta_id} - Linea {self.linea} - {self.codigo_producto_id}"


# Copia histórica de las ventas para reportes y análisis.
class HistorialVenta(models.Model):
    id_historial_venta = models.BigAutoField(primary_key=True)
    id_venta = models.IntegerField(unique=True)
    id_ruta = models.ForeignKey(Ruta, db_column='id_ruta', null=True, blank=True, on_delete=models.PROTECT)
    nit_cliente = models.ForeignKey(Cliente, db_column='nit_cliente', to_field='nit', on_delete=models.PROTECT)
    dpi_vendedor = models.ForeignKey(Vendedor, db_column='dpi_vendedor', to_field='dpi', on_delete=models.PROTECT)
    fecha_venta = models.DateTimeField()
    total_venta = models.DecimalField(max_digits=14, decimal_places=2)
    orden_visita = models.IntegerField(null=True, blank=True)
    resultado_visita = models.CharField(max_length=20, null=True, blank=True)
    observaciones_visita = models.CharField(max_length=500, null=True, blank=True)
    kilometros_estimados = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tiempo_planificado_total_min = models.IntegerField(null=True, blank=True)
    tiempo_cliente_asignado_min = models.IntegerField(null=True, blank=True)
    hora_inicio_visita = models.DateTimeField(null=True, blank=True)
    hora_fin_visita = models.DateTimeField(null=True, blank=True)
    tiempo_real_visita_min = models.IntegerField(null=True, blank=True)
    tiempo_real_ruta_min = models.IntegerField(null=True, blank=True)
    registrado_en = models.DateTimeField(default=timezone.now)
    actualizado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('historial_ventas')
        managed = _SQLITE

    def __str__(self):
        return f"Historial {self.id_historial_venta} - Venta {self.id_venta}"


# Detalle de la copia histórica, separado para no perder información.
class HistorialDetalleVenta(models.Model):
    id_historial_detalle = models.BigAutoField(primary_key=True)
    id_historial_venta = models.ForeignKey(HistorialVenta, db_column='id_historial_venta', on_delete=models.CASCADE)
    linea = models.IntegerField()
    codigo_producto = models.CharField(max_length=30)
    descripcion_producto = models.CharField(max_length=200)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    registrado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('historial_detalle_venta')
        managed = _SQLITE

    def __str__(self):
        return f"HistDet {self.id_historial_detalle} - Historial {self.id_historial_venta_id}"


# Registro de visitas creado para alimentar las pantallas del frontend.
class RegistroVisita(models.Model):
    RESULT = [
        ('VENTA', 'Venta realizada'),
        ('NO_CONCRETADA', 'No concretada'),
        ('PENDIENTE', 'Pendiente'),
    ]
    vendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, related_name='visitas')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)
    resultado = models.CharField(max_length=20, choices=RESULT)
    productos_entregados = models.JSONField(default=list, blank=True)
    evidencia_foto = models.URLField(blank=True)
    notas = models.TextField(blank=True)

    class Meta:
        db_table = 'management_registrovisita'

    def __str__(self):
        return f"Visita {self.id} - {self.vendedor} - {self.cliente} - {self.fecha}"


# Evidencias en foto o enlaces que acompañan cada visita o venta.
class EvidenciaFotografica(models.Model):
    imagen = models.ImageField(upload_to='evidencias/', null=True, blank=True)
    url = models.URLField(max_length=1024, null=True, blank=True)
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    cliente = models.ForeignKey(
        Cliente,
        to_field='nit',
        db_column='nit_cliente',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evidencias',
    )
    ruta = models.ForeignKey(
        Ruta,
        db_column='id_ruta',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evidencias',
    )
    venta = models.ForeignKey(
        Venta,
        db_column='id_venta',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evidencias',
    )
    registrada_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = db_table('evidencias_fotograficas')
        managed = _SQLITE
        ordering = ['-registrada_en']

    def __str__(self):
        identificador = self.url or (self.imagen.url if self.imagen else '')
        return f"Evidencia {self.id} - {identificador}"


# Perfil sencillo para enlazar roles a los usuarios Django.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=50, default='administrador')

    def __str__(self):
        return f"Profile {self.user.username} - {self.rol}"


# Referencia a los archivos PDF generados por los reportes.
class ReportFile(models.Model):
    uuid = models.CharField(max_length=64, unique=True)
    nombre_archivo = models.CharField(max_length=255)
    file_path = models.CharField(max_length=1024)
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_archivo} - {self.uuid}"
