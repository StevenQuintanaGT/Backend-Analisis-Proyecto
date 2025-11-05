from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClienteViewSet,
    ProductoViewSet,
    VendedorViewSet,
    RutaViewSet,
    ReportViewSet,
    CustomTokenObtainView,
    ClienteCSVImportView,
    EvidenciaFotograficaViewSet,
    EvidenciaFotograficaUploadView,
)

# Enrutador principal del API, agrupa los módulos más usados del sistema.
router = DefaultRouter()
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'vendedores', VendedorViewSet, basename='vendedor')
router.register(r'rutas', RutaViewSet, basename='ruta')
router.register(r'evidencias', EvidenciaFotograficaViewSet, basename='evidencia')

report_list = ReportViewSet.as_view({'post': 'create'})
report_download = ReportViewSet.as_view({'get': 'descargar'})

# Endpoints adicionales que no pasan por el enrutador automático.
urlpatterns = [
    path('auth/login/', CustomTokenObtainView.as_view(), name='token_obtain_pair'),
    path('importaciones/clientes/csv/', ClienteCSVImportView.as_view(), name='importar-clientes-csv'),
    path('evidencias/subir/', EvidenciaFotograficaUploadView.as_view(), name='evidencias-subir'),
    path('reportes/', report_list, name='reportes'),
    path('reportes/descargar/<str:uid>/', report_download, name='reportes-descargar'),
    path('', include(router.urls)),
]
