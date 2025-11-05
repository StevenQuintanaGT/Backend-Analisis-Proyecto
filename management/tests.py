from django.test import TestCase
from .models import Cliente, Producto, Vendedor, Ruta, ClienteRuta, CatPresentacion
from django.db import IntegrityError


# Pruebas rápidas para validar las restricciones básicas del modelo.
class ValidationTests(TestCase):
    def test_nit_unique(self):
        Cliente.objects.create(nit='000000001', nombre='A')
        with self.assertRaises(IntegrityError):
            Cliente.objects.create(nit='000000001', nombre='B')

    def test_producto_codigo_unique(self):
        CatPresentacion.objects.create(presentacion='INDIVIDUAL', descripcion='Individual')
        Producto = __import__('management.models', fromlist=['Producto']).Producto
        Producto.objects.create(codigo='C1', descripcion='X', precio_unitario=1, presentacion_id='INDIVIDUAL')
        with self.assertRaises(IntegrityError):
            Producto.objects.create(codigo='C1', descripcion='Y', precio_unitario=2, presentacion_id='INDIVIDUAL')

    def test_vendedor_nombre_trim_and_length(self):
        v = Vendedor.objects.create(dpi='0000000000001', nombre='  Juan Perez  ', sueldo=1000)
        self.assertEqual(v.nombre, 'Juan Perez')

    def test_cliente_ruta_unique(self):
        r = Ruta.objects.create(dpi_vendedor=Vendedor.objects.create(dpi='0000000000002', nombre='V', sueldo=100), fecha='2025-01-01')
        c = Cliente.objects.create(nit='000000002', nombre='C')
        ClienteRuta.objects.create(ruta=r, cliente=c, orden_visita=1, id_tiempo_cliente_id=1)
        with self.assertRaises(IntegrityError):
            ClienteRuta.objects.create(ruta=r, cliente=c, orden_visita=2, id_tiempo_cliente_id=1)
