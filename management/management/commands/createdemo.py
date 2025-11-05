from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from management.models import (
    Cliente, Producto, Vendedor, Ruta, ClienteRuta,
    CatPresentacion, CatTiempoCliente, CatResultadoVisita,
    Venta, HistorialVenta, HistorialDetalleVenta, EvidenciaFotografica
)
from django.db import OperationalError, connection
from django.utils import timezone
from PIL import Image


class Command(BaseCommand):
    # Crea un administrador por defecto y datos de ejemplo para probar el sistema.
    help = 'Create demo admin and sample data (compatible con esquema SQL proporcionado)'

    @staticmethod
    def build_sample_image():
        buffer = BytesIO()
        img = Image.new('RGB', (2, 2), color=(0, 128, 255))
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Created superuser admin/admin123'))

        # Cargamos catálogos mínimos; si las tablas no existen (por ejemplo en SQLite) seguimos sin fallar.
        try:
            CatPresentacion.objects.get_or_create(presentacion='INDIVIDUAL', defaults={'descripcion': 'Presentación individual'})
            CatPresentacion.objects.get_or_create(presentacion='DOCENA', defaults={'descripcion': 'Presentación por docena'})
            CatTiempoCliente.objects.get_or_create(id_tiempo_cliente=1, defaults={'minutos': 60, 'descripcion': '1 hora'})
            CatTiempoCliente.objects.get_or_create(id_tiempo_cliente=2, defaults={'minutos': 120, 'descripcion': '2 horas'})
            CatResultadoVisita.objects.get_or_create(resultado_visita='VENTA', defaults={'descripcion': 'Venta concretada'})
            CatResultadoVisita.objects.get_or_create(resultado_visita='NO_CONCRETADA', defaults={'descripcion': 'Sin venta'})
            CatResultadoVisita.objects.get_or_create(resultado_visita='PENDIENTE', defaults={'descripcion': 'Pendiente de resultado'})
        except OperationalError:
            # Si faltan tablas del esquema original, avisamos y continuamos.
            self.stdout.write(self.style.WARNING('Catalog tables (sistema.*) not present; skipping catalog seed'))

        # Creamos clientes, productos, vendedores y rutas solo si las tablas están disponibles.
        try:
            clientes_info = [
                ('000000001', {'nombre': 'Cliente Uno', 'direccion': 'Calle 1', 'correo_electronico': 'c1@example.com', 'estatus_credito': 'A'}),
                ('000000002', {'nombre': 'Cliente Dos', 'direccion': 'Calle 2', 'correo_electronico': 'c2@example.com', 'estatus_credito': 'B'}),
                ('000000003', {'nombre': 'Cliente Tres', 'direccion': 'Calle 3', 'correo_electronico': 'c3@example.com', 'estatus_credito': 'A'}),
                ('000000004', {'nombre': 'Cliente Cuatro', 'direccion': 'Calle 4', 'correo_electronico': 'c4@example.com', 'estatus_credito': 'C'}),
                ('000000005', {'nombre': 'Cliente Cinco', 'direccion': 'Calle 5', 'correo_electronico': 'c5@example.com', 'estatus_credito': 'B'}),
            ]
            clientes = []
            for nit, defaults in clientes_info:
                cliente, _ = Cliente.objects.get_or_create(nit=nit, defaults=defaults)
                clientes.append(cliente)

            productos_info = [
                ('P001', {'descripcion': 'Producto 1', 'color': 'Rojo', 'precio_unitario': Decimal('10.00'), 'presentacion_id': 'INDIVIDUAL'}),
                ('P002', {'descripcion': 'Producto 2', 'color': 'Azul', 'precio_unitario': Decimal('120.00'), 'presentacion_id': 'DOCENA'}),
                ('P003', {'descripcion': 'Producto 3', 'color': 'Verde', 'precio_unitario': Decimal('55.50'), 'presentacion_id': 'INDIVIDUAL'}),
                ('P004', {'descripcion': 'Producto 4', 'color': 'Negro', 'precio_unitario': Decimal('89.99'), 'presentacion_id': 'DOCENA'}),
            ]
            productos = []
            for codigo, defaults in productos_info:
                producto, _ = Producto.objects.get_or_create(codigo=codigo, defaults=defaults)
                productos.append(producto)

            vendedores_info = [
                ('0000000000001', {'nombre': 'Vendedor Demo', 'sueldo': Decimal('1500.00'), 'nivel_exito_porcent': 68}),
                ('0000000000002', {'nombre': 'Vendedor Expo', 'sueldo': Decimal('1750.00'), 'nivel_exito_porcent': 82}),
            ]
            vendedores = []
            for dpi, defaults in vendedores_info:
                vendedor, _ = Vendedor.objects.get_or_create(dpi=dpi, defaults=defaults)
                vendedores.append(vendedor)

            tiempo_default = CatTiempoCliente.objects.filter(id_tiempo_cliente=1).first()
            resultado_venta = CatResultadoVisita.objects.filter(resultado_visita='VENTA').first()
            resultado_pend = CatResultadoVisita.objects.filter(resultado_visita='PENDIENTE').first()

            fecha_base = timezone.now()
            rutas_creadas = []
            ventas_creadas = []
            for offset, vendedor in enumerate(vendedores):
                for day in range(3):
                    fecha_ruta = (fecha_base - timedelta(days=offset * 3 + day)).date()
                    ruta, _ = Ruta.objects.get_or_create(
                        dpi_vendedor=vendedor,
                        fecha=fecha_ruta,
                        defaults={
                            'nombre': f"Ruta {vendedor.nombre.split()[0]} {fecha_ruta.isoformat()}",
                            'kilometros_estimados': Decimal('120.0') - Decimal(offset * 10 + day * 5),
                            'tiempo_planificado_min': 180,
                            'tiempo_real_min': 165,
                            'resultado_global': 'Planificado'
                        }
                    )
                    if not ruta.nombre:
                        ruta.nombre = f"Ruta {vendedor.nombre.split()[0]} {fecha_ruta.isoformat()}"
                        ruta.save(update_fields=['nombre'])
                    rutas_creadas.append(ruta)

                    for idx, cliente in enumerate(clientes[:3], start=1):
                        cr_defaults = {
                            'orden_visita': idx,
                            'id_tiempo_cliente': tiempo_default,
                            'observaciones': 'Visita planificada',
                        }
                        if resultado_pend:
                            cr_defaults['resultado_visita'] = resultado_pend

                        ClienteRuta.objects.get_or_create(
                            ruta=ruta,
                            cliente=cliente,
                            defaults=cr_defaults
                        )

                    venta_cliente = clientes[0]
                    producto = productos[(offset + day) % len(productos)]
                    fecha_venta = fecha_base - timedelta(days=offset * 3 + day)
                    venta = Venta.objects.filter(nit_cliente=venta_cliente, fecha=fecha_venta).first()
                    if not venta:
                        venta = Venta.objects.create(
                            fecha=fecha_venta,
                            nit_cliente=venta_cliente,
                            id_ruta=ruta,
                            total=producto.precio_unitario * 3,
                            creado_en=fecha_venta,
                            actualizado_en=fecha_venta,
                        )
                    else:
                        venta.id_ruta = ruta
                        venta.total = producto.precio_unitario * 3
                        venta.save(update_fields=['id_ruta', 'total'])
                    ventas_creadas.append(venta)

                    if connection.vendor == 'sqlite':
                        cursor = connection.cursor()
                        sql = (
                            "INSERT OR IGNORE INTO detalle_venta (id_venta, linea, codigo_producto, cantidad, precio_unitario) "
                            f"VALUES ({venta.id_venta}, 1, '{producto.codigo}', 3, {float(producto.precio_unitario)})"
                        )
                        cursor.execute(sql)

                    if not HistorialVenta.objects.filter(id_venta=venta.id_venta).exists():
                        historial = HistorialVenta.objects.create(
                            id_venta=venta.id_venta,
                            id_ruta=ruta,
                            nit_cliente=venta_cliente,
                            dpi_vendedor=vendedor,
                            fecha_venta=fecha_venta,
                            total_venta=venta.total,
                            orden_visita=1,
                            resultado_visita='VENTA',
                            observaciones_visita='Visita exitosa',
                            kilometros_estimados=ruta.kilometros_estimados,
                            tiempo_planificado_total_min=ruta.tiempo_planificado_min,
                            tiempo_cliente_asignado_min=tiempo_default.minutos if tiempo_default else None,
                            hora_inicio_visita=fecha_venta,
                            hora_fin_visita=fecha_venta + timedelta(minutes=35),
                            tiempo_real_visita_min=35,
                            tiempo_real_ruta_min=ruta.tiempo_real_min or 150,
                        )

                        HistorialDetalleVenta.objects.create(
                            id_historial_venta=historial,
                            linea=1,
                            codigo_producto=producto.codigo,
                            descripcion_producto=producto.descripcion,
                            cantidad=3,
                            precio_unitario=producto.precio_unitario,
                            subtotal=producto.precio_unitario * 3,
                        )

            if rutas_creadas and ventas_creadas:
                muestras = [
                    {
                        'descripcion': 'Comprobante fotográfico de la visita principal',
                        'cliente': clientes[0],
                        'ruta': rutas_creadas[0],
                        'venta': ventas_creadas[0],
                        'offset': 0,
                        'nombre': 'demo_principal.png',
                    },
                    {
                        'descripcion': 'Evidencia de entrega en tienda secundaria',
                        'cliente': clientes[1] if len(clientes) > 1 else clientes[0],
                        'ruta': rutas_creadas[1] if len(rutas_creadas) > 1 else rutas_creadas[0],
                        'venta': ventas_creadas[1] if len(ventas_creadas) > 1 else ventas_creadas[0],
                        'offset': 2,
                        'nombre': 'demo_secundaria.png',
                    },
                ]

                for muestra in muestras:
                    defaults = {
                        'registrada_en': timezone.now() - timedelta(hours=muestra['offset']),
                    }
                    evidencia, created = EvidenciaFotografica.objects.get_or_create(
                        descripcion=muestra['descripcion'],
                        cliente=muestra['cliente'],
                        ruta=muestra['ruta'],
                        venta=muestra['venta'],
                        defaults=defaults,
                    )
                    if created or not evidencia.imagen:
                        evidencia.imagen.save(
                            muestra['nombre'],
                            ContentFile(self.build_sample_image()),
                            save=True,
                        )
        except OperationalError as exc:
            self.stdout.write(self.style.WARNING(f'sistema.* tables not present; skipping sample data creation ({exc})'))

        self.stdout.write(self.style.SUCCESS('Demo data created (if DB schema exists)'))
