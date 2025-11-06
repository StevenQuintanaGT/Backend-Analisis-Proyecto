from datetime import date, datetime
from decimal import Decimal
import csv
import io

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
import uuid
import tempfile
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.utils.dateparse import parse_date, parse_datetime

from django.db import transaction
from django.db.models import Avg, Count
from django.db.models.deletion import ProtectedError
from .models import (
    Cliente, Producto, Venta, DetalleVenta, Vendedor, RegistroVisita, Ruta, ClienteRuta,
    HistorialVenta, ReportFile, EvidenciaFotografica,
)
from .serializers import (
    ClienteSerializer, ProductoSerializer, VentaSerializer, DetalleVentaSerializer, VendedorSerializer,
    RegistroVisitaSerializer, RutaSerializer, ClienteRutaSerializer, ReportFileSerializer,
    EvidenciaFotograficaSerializer,
)

# Reordenamos la información recibida para guardar evidencias sin importar el formato del formulario.
def _build_evidencia_payload(data, files):
    payload = {}
    getlist = getattr(data, 'getlist', None)
    for key in data.keys():
        if getlist:
            values = data.getlist(key)
        else:
            value = data.get(key)
            values = [value] if value is not None else []
        if not values:
            continue
        payload[key] = values[0] if len(values) == 1 else values

    archivo = files.get('archivo')
    imagen_subida = files.get('imagen')
    if archivo:
        payload['imagen'] = archivo
    elif imagen_subida:
        payload['imagen'] = imagen_subida

    payload.pop('archivo', None)

    nit_cliente = payload.get('nit_cliente')
    if nit_cliente and not payload.get('cliente'):
        payload['cliente'] = nit_cliente
    payload.pop('nit_cliente', None)

    id_ruta = payload.get('id_ruta')
    if id_ruta and not payload.get('ruta'):
        payload['ruta'] = id_ruta
    payload.pop('id_ruta', None)

    id_venta = payload.get('id_venta')
    if id_venta and not payload.get('venta'):
        payload['venta'] = id_venta
    payload.pop('id_venta', None)

    return payload


class CustomTokenObtainView(TokenObtainPairView):
    # Vista de autenticación que también devuelve información básica del usuario.
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)
        if resp.status_code != 200:
            return resp
        data = resp.data
        # Adjuntamos datos simples del usuario para que el frontend no haga otra consulta.
        from django.contrib.auth.models import User
        username = request.data.get('username')
        try:
            user = User.objects.get(username=username)
            data['user'] = {'id': user.id, 'username': user.username, 'email': user.email}
        except User.DoesNotExist:
            data['user'] = None
        return Response(data)


class ClienteViewSet(viewsets.ModelViewSet):
    # CRUD de clientes con un filtro rápido por NIT.
    queryset = Cliente.objects.all().order_by('nit')
    serializer_class = ClienteSerializer

    def list(self, request, *args, **kwargs):
        nit = request.GET.get('n') or request.GET.get('nit')
        qs = self.get_queryset()
        if nit:
            qs = qs.filter(nit__iexact=nit)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ProductoViewSet(viewsets.ModelViewSet):
    # Administración de productos y búsqueda por código.
    queryset = Producto.objects.all().order_by('codigo')
    serializer_class = ProductoSerializer

    def list(self, request, *args, **kwargs):
        codigo = request.GET.get('codigo')
        qs = self.get_queryset()
        if codigo:
            qs = qs.filter(codigo__iexact=codigo)
        if codigo:
            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)

# Control de vendedores y un endpoint auxiliar para registrar visitas.
class VendedorViewSet(viewsets.ModelViewSet):
    queryset = Vendedor.objects.all().order_by('dpi')
    serializer_class = VendedorSerializer

    @action(detail=True, methods=['get', 'post'])
    def visitas(self, request, pk=None):
        vendedor = get_object_or_404(Vendedor, pk=pk)
        if request.method == 'GET':
            visitas = vendedor.visitas.all()
            serializer = RegistroVisitaSerializer(visitas, many=True)
            return Response(serializer.data)
        else:
            data = request.data.copy()
            data['vendedor'] = vendedor.id
            serializer = RegistroVisitaSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
# Gestión de rutas y acciones relacionadas con los recorridos.
class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.all().order_by('id_ruta')
    serializer_class = RutaSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        with transaction.atomic():
            Venta.objects.filter(id_ruta=instance).update(id_ruta=None)
            HistorialVenta.objects.filter(id_ruta=instance).update(id_ruta=None)
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "No se pudo eliminar la ruta porque aún tiene dependencias protegidas."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'])
    def recorridos(self, request, pk=None):
        ruta = get_object_or_404(Ruta, pk=pk)
        if request.method == 'GET':
            # Entregamos las ventas vinculadas a la ruta como historial de recorridos.
            ventas = Venta.objects.filter(id_ruta=ruta)
            serializer = VentaSerializer(ventas, many=True)
            return Response(serializer.data)
        else:
            data = request.data.copy()
            data['id_ruta'] = ruta.id_ruta
            # Esperamos fecha, cliente y total para registrar la venta.
            serializer = VentaSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def comparacion_tiempos(self, request, pk=None):
        ruta = get_object_or_404(Ruta, pk=pk)
        registro = []
        for cr in ruta.clienteruta_set.all():
            # Minutos planificados tomados del catálogo.
            planned = None
            if cr.id_tiempo_cliente and hasattr(cr.id_tiempo_cliente, 'minutos'):
                planned = cr.id_tiempo_cliente.minutos
            # Promedio de minutos reales usando el historial de ventas.
            avg = HistorialVenta.objects.filter(id_ruta=ruta, nit_cliente=cr.cliente).aggregate(avg_real=Avg('tiempo_real_visita_min'))
            avg_real = avg.get('avg_real')
            registro.append({'cliente': cr.cliente.nombre, 'planned': planned, 'avg_real': avg_real})
        return Response(registro)

# Permite listar, crear y actualizar evidencias con filtros sencillos.
class EvidenciaFotograficaViewSet(viewsets.ModelViewSet):
    queryset = EvidenciaFotografica.objects.select_related('cliente', 'ruta', 'venta').order_by('-registrada_en')
    serializer_class = EvidenciaFotograficaSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def _normalize_payload(self, request):
        return _build_evidencia_payload(request.data, request.FILES)

    def get_queryset(self):
        qs = super().get_queryset()
        nit = self.request.query_params.get('nit_cliente') or self.request.query_params.get('cliente')
        if nit:
            qs = qs.filter(cliente__nit=nit)
        ruta_id = self.request.query_params.get('id_ruta') or self.request.query_params.get('ruta')
        if ruta_id:
            try:
                qs = qs.filter(ruta__id_ruta=int(ruta_id))
            except ValueError:
                qs = qs.none()
        venta_id = self.request.query_params.get('id_venta') or self.request.query_params.get('venta')
        if venta_id:
            try:
                qs = qs.filter(venta__id_venta=int(venta_id))
            except ValueError:
                qs = qs.none()
        return qs

    def create(self, request, *args, **kwargs):
        data = self._normalize_payload(request)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = self._normalize_payload(request)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


# Generamos un PDF ligero con resúmenes de cada módulo.
class ReportViewSet(viewsets.ViewSet):
    permission_classes = ()

    def create(self, request):
        # Esperamos tipo de reporte, rango de fechas y filtros sencillos.
        tipo = request.data.get('tipo', 'clientes')
        fecha_inicio = request.data.get('fecha_inicio')
        fecha_fin = request.data.get('fecha_fin')
        filtros = request.data.get('filtros', {})

        tipo_raw = str(tipo or '').lower()
        tipo_map = {
            'clientes': 'clientes',
            'listado_clientes': 'clientes',
            'productos': 'productos',
            'listado_productos': 'productos',
            'vendedores': 'vendedores',
            'listado_vendedores': 'vendedores',
            'rutas': 'rutas',
            'listado_rutas': 'rutas',
            'ventas': 'ventas',
            'historial': 'historial',
            'historial_ventas': 'historial',
            'comparacion': 'comparacion',
            'comparacion_tiempos': 'comparacion',
        }
        tipo_normalized = tipo_map.get(tipo_raw, tipo_raw)

        uid = str(uuid.uuid4())
        tmp_dir = tempfile.gettempdir()
        filename = f"report_{tipo_normalized}_{uid}.pdf"
        file_path = os.path.join(tmp_dir, filename)
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter
        margin_x = 72
        margin_top = 72
        margin_bottom = 72
        line_height = 14
        generated_at = timezone.now()
        filtros_desc = filtros or {}
        y = height - margin_top

        def start_page():
            nonlocal y
            y = height - margin_top
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin_x, y, f"Reporte: {tipo_normalized.title()}")
            y -= 18
            c.setFont("Helvetica", 10)
            c.drawString(margin_x, y, f"Generado: {generated_at.isoformat()}")
            y -= 14
            c.drawString(margin_x, y, f"Filtros: {filtros_desc if filtros_desc else 'N/A'}")
            y -= 24

        def ensure_space(lines_needed=1):
            nonlocal y
            if y - (line_height * lines_needed) < margin_bottom:
                c.showPage()
                start_page()

        start_page()

        def normalize_date(value):
            if not value:
                return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            parsed = parse_date(str(value))
            if parsed:
                return parsed
            parsed_dt = parse_datetime(str(value))
            if parsed_dt:
                return parsed_dt.date()
            return None

        def draw_table(columns, rows, summary=None):
            nonlocal y
            ensure_space(2)
            c.setFont("Helvetica-Bold", 11)
            for label, xpos, align in columns:
                if align == 'right':
                    c.drawRightString(xpos, y, label)
                else:
                    c.drawString(xpos, y, label)
            y -= 16
            c.setFont("Helvetica", 10)

            if not rows:
                ensure_space(1)
                c.drawString(margin_x, y, "Sin registros para los filtros indicados.")
                y -= line_height
            else:
                for row in rows:
                    ensure_space(1)
                    for (label, xpos, align), value in zip(columns, row):
                        text = str(value) if value is not None else ''
                        if align == 'right':
                            c.drawRightString(xpos, y, text)
                        else:
                            c.drawString(xpos, y, text)
                    y -= line_height

            if summary:
                ensure_space(len(summary))
                c.setFont("Helvetica-Bold", 10)
                for line in summary:
                    c.drawString(margin_x, y, line)
                    y -= line_height
                c.setFont("Helvetica", 10)

        def report_clientes():
            qs = Cliente.objects.all().order_by('nombre')
            estatus = filtros.get('estatus') or filtros.get('estatus_credito')
            if estatus:
                qs = qs.filter(estatus_credito=estatus)
            rows = [
                (
                    cliente.nit,
                    cliente.nombre[:28],
                    cliente.estatus_credito,
                    (cliente.correo_electronico or '')[:32],
                )
                for cliente in qs
            ]
            summary = [f"Total clientes: {qs.count()}"]
            columns = [
                ("NIT", margin_x, 'left'),
                ("Nombre", margin_x + 90, 'left'),
                ("Estatus", margin_x + 300, 'left'),
                ("Correo", margin_x + 380, 'left'),
            ]
            draw_table(columns, rows, summary)

        def report_productos():
            qs = Producto.objects.select_related('presentacion').all().order_by('descripcion')
            presentacion = filtros.get('presentacion')
            if presentacion:
                qs = qs.filter(presentacion__presentacion=presentacion)
            rows = [
                (
                    prod.codigo,
                    prod.descripcion[:30],
                    prod.presentacion.presentacion if prod.presentacion else '',
                    f"{prod.precio_unitario:.2f}",
                )
                for prod in qs
            ]
            summary = [f"Total productos: {qs.count()}"]
            columns = [
                ("Código", margin_x, 'left'),
                ("Descripción", margin_x + 80, 'left'),
                ("Presentación", margin_x + 300, 'left'),
                ("Precio", margin_x + 460, 'right'),
            ]
            draw_table(columns, rows, summary)

        def report_vendedores():
            qs = Vendedor.objects.all().order_by('nombre')
            nivel_min = filtros.get('nivel_min')
            if nivel_min is not None:
                try:
                    qs = qs.filter(nivel_exito_porcent__gte=int(nivel_min))
                except ValueError:
                    pass
            rows = [
                (
                    vend.dpi,
                    vend.nombre[:26],
                    f"{vend.sueldo:.2f}",
                    f"{vend.nivel_exito_porcent or 0}%",
                )
                for vend in qs
            ]
            summary = [f"Total vendedores: {qs.count()}"]
            columns = [
                ("DPI", margin_x, 'left'),
                ("Nombre", margin_x + 120, 'left'),
                ("Sueldo", margin_x + 360, 'right'),
                ("Éxito", margin_x + 460, 'right'),
            ]
            draw_table(columns, rows, summary)

        def report_rutas():
            qs = Ruta.objects.select_related('dpi_vendedor').all().order_by('-fecha')
            fecha_desde = normalize_date(filtros.get('desde') or filtros.get('fecha_desde') or fecha_inicio)
            fecha_hasta = normalize_date(filtros.get('hasta') or filtros.get('fecha_hasta') or fecha_fin)
            vendedor = filtros.get('dpi_vendedor')
            if fecha_desde:
                qs = qs.filter(fecha__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha__lte=fecha_hasta)
            if vendedor:
                qs = qs.filter(dpi_vendedor__dpi=vendedor)
            rows = [
                (
                    ruta.id_ruta,
                    ruta.fecha.strftime('%Y-%m-%d'),
                    (ruta.nombre or '')[:24],
                    ruta.dpi_vendedor.nombre[:24] if ruta.dpi_vendedor else '-',
                    f"{ruta.kilometros_estimados or 0:.2f}",
                    ruta.tiempo_planificado_min or '-',
                    ruta.tiempo_real_min or '-',
                )
                for ruta in qs
            ]
            summary = [f"Total rutas: {qs.count()}"]
            columns = [
                ("Ruta", margin_x + 30, 'right'),
                ("Fecha", margin_x + 90, 'left'),
                ("Nombre", margin_x + 200, 'left'),
                ("Vendedor", margin_x + 360, 'left'),
                ("KM", margin_x + 440, 'right'),
                ("Plan (min)", margin_x + 510, 'right'),
                ("Real (min)", margin_x + 580, 'right'),
            ]
            draw_table(columns, rows, summary)

        def report_ventas():
            qs = Venta.objects.select_related('nit_cliente', 'id_ruta').all().order_by('-fecha')
            fecha_desde = normalize_date(filtros.get('desde') or fecha_inicio)
            fecha_hasta = normalize_date(filtros.get('hasta') or fecha_fin)
            cliente = filtros.get('nit_cliente')
            if fecha_desde:
                qs = qs.filter(fecha__date__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha__date__lte=fecha_hasta)
            if cliente:
                qs = qs.filter(nit_cliente__nit=cliente)
            total_general = Decimal('0.00')
            rows = []
            for venta in qs:
                total_general += venta.total
                nombre_cliente = venta.nit_cliente.nombre if venta.nit_cliente else venta.nit_cliente_id
                rows.append(
                    (
                        venta.fecha.strftime('%Y-%m-%d'),
                        nombre_cliente[:24],
                        f"{venta.total:.2f}",
                        str(venta.id_ruta_id or '-'),
                    )
                )
            summary = [
                f"Total ventas: {qs.count()}",
                f"Monto acumulado: Q{total_general:.2f}",
            ]
            columns = [
                ("Fecha", margin_x, 'left'),
                ("Cliente", margin_x + 120, 'left'),
                ("Total Q", margin_x + 360, 'right'),
                ("Ruta", margin_x + 440, 'right'),
            ]
            draw_table(columns, rows, summary)

        def report_historial():
            qs = HistorialVenta.objects.select_related('nit_cliente', 'dpi_vendedor').all().order_by('-fecha_venta')
            fecha_desde = normalize_date(filtros.get('desde') or fecha_inicio)
            fecha_hasta = normalize_date(filtros.get('hasta') or fecha_fin)
            vendedor = filtros.get('dpi_vendedor')
            if fecha_desde:
                qs = qs.filter(fecha_venta__date__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha_venta__date__lte=fecha_hasta)
            if vendedor:
                qs = qs.filter(dpi_vendedor__dpi=vendedor)
            total_general = Decimal('0.00')
            rows = []
            for hist in qs:
                total_general += hist.total_venta
                rows.append(
                    (
                        hist.fecha_venta.strftime('%Y-%m-%d'),
                        (hist.nit_cliente.nombre if hist.nit_cliente else hist.nit_cliente_id)[:20],
                        (hist.dpi_vendedor.nombre if hist.dpi_vendedor else hist.dpi_vendedor_id)[:18],
                        f"{hist.total_venta:.2f}",
                        (hist.resultado_visita or '-')[:10],
                    )
                )
            summary = [
                f"Total registros historial: {qs.count()}",
                f"Total facturado: Q{total_general:.2f}",
            ]
            columns = [
                ("Fecha", margin_x, 'left'),
                ("Cliente", margin_x + 110, 'left'),
                ("Vendedor", margin_x + 260, 'left'),
                ("Total Q", margin_x + 430, 'right'),
                ("Resultado", margin_x + 520, 'left'),
            ]
            draw_table(columns, rows, summary)

        def report_comparacion():
            qs = Ruta.objects.select_related('dpi_vendedor').annotate(
                total_clientes=Count('clienteruta', distinct=True),
                total_ventas=Count('venta', distinct=True),
                avg_historial=Avg('historialventa__tiempo_real_visita_min'),
            ).order_by('-fecha')
            fecha_desde = normalize_date(filtros.get('desde') or fecha_inicio)
            fecha_hasta = normalize_date(filtros.get('hasta') or fecha_fin)
            vendedor = filtros.get('dpi_vendedor')
            if fecha_desde:
                qs = qs.filter(fecha__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha__lte=fecha_hasta)
            if vendedor:
                qs = qs.filter(dpi_vendedor__dpi=vendedor)
            rows = []
            for ruta in qs:
                rows.append(
                    (
                        ruta.id_ruta,
                        ruta.fecha.strftime('%Y-%m-%d'),
                        ruta.dpi_vendedor.nombre[:20] if ruta.dpi_vendedor else '-',
                        ruta.tiempo_planificado_min or '-',
                        ruta.tiempo_real_min or '-',
                        f"{ruta.avg_historial:.1f}" if ruta.avg_historial is not None else '-',
                    )
                )
            summary = [
                f"Total rutas analizadas: {qs.count()}",
            ]
            columns = [
                ("Ruta", margin_x + 30, 'right'),
                ("Fecha", margin_x + 90, 'left'),
                ("Vendedor", margin_x + 200, 'left'),
                ("Plan (min)", margin_x + 360, 'right'),
                ("Real (min)", margin_x + 440, 'right'),
                ("Prom Hist (min)", margin_x + 520, 'right'),
            ]
            draw_table(columns, rows, summary)

        if tipo_normalized == 'clientes':
            report_clientes()
        elif tipo_normalized == 'productos':
            report_productos()
        elif tipo_normalized == 'vendedores':
            report_vendedores()
        elif tipo_normalized == 'rutas':
            report_rutas()
        elif tipo_normalized == 'ventas':
            report_ventas()
        elif tipo_normalized == 'historial':
            report_historial()
        elif tipo_normalized == 'comparacion':
            report_comparacion()
        else:
            draw_table(
                [("Información", margin_x, 'left')],
                [[f"Tipo de reporte '{tipo}' no implementado."]],
            )

        c.save()

        rf = ReportFile.objects.create(uuid=uid, nombre_archivo=filename, file_path=file_path)
        serializer = ReportFileSerializer(rf)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='descargar/(?P<uid>[^/.]+)')
    def descargar(self, request, uid=None):
        try:
            rf = ReportFile.objects.get(uuid=uid)
            if not os.path.exists(rf.file_path):
                raise Http404('Archivo no encontrado')
            return FileResponse(open(rf.file_path, 'rb'), as_attachment=True, filename=rf.nombre_archivo)
        except ReportFile.DoesNotExist:
            raise Http404('Reporte no existe')

# Importamos clientes desde un CSV validando encabezados y datos clave.
class ClienteCSVImportView(APIView):
    parser_classes = (MultiPartParser,)
    expected_headers = ['nit', 'nombre', 'direccion', 'correo_electronico', 'estatus_credito']

    def post(self, request):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response({"detail": "Cargue un archivo CSV en el campo 'archivo'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            raw_content = archivo.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            return Response({"detail": "El archivo CSV debe estar codificado en UTF-8."}, status=status.HTTP_400_BAD_REQUEST)

        if not raw_content.strip():
            return Response({"detail": "El archivo CSV está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(raw_content))
        if not reader.fieldnames:
            return Response({"detail": "El archivo CSV no contiene encabezados."}, status=status.HTTP_400_BAD_REQUEST)

        normalized_headers = [h.strip().lower() for h in reader.fieldnames]
        missing = [header for header in self.expected_headers if header not in normalized_headers]
        if missing:
            return Response({
                "detail": "Encabezados faltantes en el CSV.",
                "faltantes": missing,
                "esperados": self.expected_headers,
            }, status=status.HTTP_400_BAD_REQUEST)

        errores = []
        creados = 0
        actualizados = 0
        now = timezone.now()

        with transaction.atomic():
            for idx, row in enumerate(reader, start=2):
                normalized_row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                if not any(normalized_row.values()):
                    continue  # fila en blanco

                data = {
                    'nit': normalized_row.get('nit') or '',
                    'nombre': normalized_row.get('nombre') or '',
                    'direccion': normalized_row.get('direccion') or None,
                    'correo_electronico': normalized_row.get('correo_electronico') or None,
                    'estatus_credito': (normalized_row.get('estatus_credito') or 'B')[:2],
                }

                existing = Cliente.objects.filter(nit=data['nit']).first()
                serializer = ClienteSerializer(existing, data=data) if existing else ClienteSerializer(data=data)

                if serializer.is_valid():
                    save_kwargs = {'actualizado_en': now}
                    if not existing:
                        save_kwargs['creado_en'] = now
                    serializer.save(**save_kwargs)
                    if existing:
                        actualizados += 1
                    else:
                        creados += 1
                else:
                    errores.append({'fila': idx, 'errores': serializer.errors})

            if errores:
                transaction.set_rollback(True)
                return Response({
                    'detail': 'Se encontraron errores de validación.',
                    'errores': errores,
                }, status=status.HTTP_400_BAD_REQUEST)

        status_code = status.HTTP_201_CREATED if creados else status.HTTP_200_OK
        return Response({
            'creados': creados,
            'actualizados': actualizados,
        }, status=status_code)

# Endpoint dedicado para subir evidencias con archivos grandes.
class EvidenciaFotograficaUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        archivo = request.FILES.get('archivo') or request.FILES.get('imagen')
        if not archivo:
            return Response({"detail": "Cargue un archivo en el campo 'archivo' o 'imagen'."}, status=status.HTTP_400_BAD_REQUEST)

        payload = _build_evidencia_payload(request.data, request.FILES)
        if 'imagen' not in payload:
            payload['imagen'] = archivo

        serializer = EvidenciaFotograficaSerializer(data=payload, context={'request': request})
        serializer.is_valid(raise_exception=True)
        evidencia = serializer.save()
        response_data = EvidenciaFotograficaSerializer(evidencia, context={'request': request}).data
        return Response(response_data, status=status.HTTP_201_CREATED)
