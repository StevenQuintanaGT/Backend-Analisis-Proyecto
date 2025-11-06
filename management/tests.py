from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    Cliente,
    Producto,
    Vendedor,
    Ruta,
    ClienteRuta,
    CatPresentacion,
    CatTiempoCliente,
    CatResultadoVisita,
)


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
        tiempo, _ = CatTiempoCliente.objects.get_or_create(id_tiempo_cliente=1, defaults={'minutos': 10, 'descripcion': 'Breve'})
        ClienteRuta.objects.create(ruta=r, cliente=c, orden_visita=1, id_tiempo_cliente=tiempo)
        with self.assertRaises(IntegrityError):
            ClienteRuta.objects.create(ruta=r, cliente=c, orden_visita=2, id_tiempo_cliente_id=1)


class RutaClientesAPITests(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(username='tester', password='secret')
        self.client_api.force_authenticate(user=self.user)
        self.vendedor = Vendedor.objects.create(dpi='9999999999999', nombre='Ruta Vendedor', sueldo=100)
        self.tiempo, _ = CatTiempoCliente.objects.get_or_create(id_tiempo_cliente=1, defaults={'minutos': 15, 'descripcion': 'Corto'})
        CatResultadoVisita.objects.get_or_create(resultado_visita='PENDIENTE', defaults={'descripcion': 'Pendiente'})
        self.cliente1 = Cliente.objects.create(nit='100000001', nombre='Cliente 1')
        self.cliente2 = Cliente.objects.create(nit='100000002', nombre='Cliente 2')

    def test_crear_ruta_con_clientes(self):
        respuesta = self.client_api.post(
            '/api/rutas/',
            {
                'dpi_vendedor': self.vendedor.dpi,
                'fecha': '2025-11-05',
                'nombre': 'Ruta Norte',
                'clientes': [
                    {'nit_cliente': self.cliente1.nit, 'orden_visita': 1, 'id_tiempo_cliente': self.tiempo.id_tiempo_cliente},
                    {'nit_cliente': self.cliente2.nit, 'orden_visita': 2, 'id_tiempo_cliente': self.tiempo.id_tiempo_cliente},
                ],
            },
            format='json',
        )

        self.assertEqual(respuesta.status_code, 201)
        data = respuesta.json()
        self.assertEqual(data['estado'], 'PENDIENTE')
        self.assertEqual(len(data['clienterutas']), 2)
        nombres = [cr['cliente']['nombre'] for cr in data['clienterutas']]
        self.assertEqual(nombres, ['Cliente 1', 'Cliente 2'])
        ruta = Ruta.objects.get(id_ruta=data['id_ruta'])
        clientes_ruta = ClienteRuta.objects.filter(ruta=ruta).order_by('orden_visita')
        self.assertEqual(clientes_ruta.count(), 2)
        self.assertEqual(clientes_ruta.first().cliente, self.cliente1)

    def test_error_cliente_inexistente(self):
        respuesta = self.client_api.post(
            '/api/rutas/',
            {
                'dpi_vendedor': self.vendedor.dpi,
                'fecha': '2025-11-05',
                'estado': 'CANCELADA',
                'clientes': [{'nit_cliente': '000000000', 'orden_visita': 1, 'id_tiempo_cliente': self.tiempo.id_tiempo_cliente}],
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, 400)
        data = respuesta.json()
        self.assertIn('clientes', data)
