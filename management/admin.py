from django.contrib import admin
from .models import (
    Cliente, Producto, Venta, DetalleVenta, Vendedor, ClienteRuta, RegistroVisita,
    Ruta, HistorialVenta, HistorialDetalleVenta, UserProfile, ReportFile,
    CatPresentacion, CatEstatusCredito, CatResultadoVisita, CatTiempoCliente
)

# Registramos los modelos principales para revisarlos rápido en el panel de administración.
admin.site.register(Cliente)
admin.site.register(Producto)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Vendedor)
admin.site.register(Ruta)
admin.site.register(ClienteRuta)
admin.site.register(HistorialVenta)
admin.site.register(HistorialDetalleVenta)
admin.site.register(RegistroVisita)
admin.site.register(UserProfile)
admin.site.register(ReportFile)
admin.site.register(CatPresentacion)
admin.site.register(CatEstatusCredito)
admin.site.register(CatResultadoVisita)
admin.site.register(CatTiempoCliente)
