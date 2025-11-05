import os
import sys
import random
from io import BytesIO
from PIL import Image
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

def build_png_sample():
    buf = BytesIO()
    img = Image.new("RGB", (2, 2), color=(255, 0, 0))
    img.save(buf, format="PNG")
    return buf.getvalue()


PNG_SAMPLE = build_png_sample()

django.setup()

from rest_framework.test import APIClient  # noqa: E402
from management.models import ClienteRuta, CatTiempoCliente  # noqa: E402

client = APIClient()
client.defaults['HTTP_HOST'] = 'localhost'


def assert_status(response, expected=200, context=""):
    if response.status_code != expected:
        payload = getattr(response, "data", None)
        print(f"[FAIL] {context} -> status={response.status_code}, data={payload}")
        sys.exit(1)


print("[INFO] Authenticating...")
resp = client.post(
    "/api/auth/login/",
    {"username": "admin", "password": "admin123"},
    format="json",
)
assert_status(resp, 200, "login")
access = resp.data["access"]
client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
print("[OK] Authenticated")

suffix = random.randint(100000000, 999999999)
client_nit = str(suffix)

print("[INFO] Creating cliente...")
resp = client.post(
    "/api/clientes/",
    {
        "nit": client_nit,
        "nombre": "Cliente API",
        "direccion": "Zona 1",
        "correo_electronico": f"cliente{suffix}@example.com",
        "estatus_credito": "A",
    },
    format="json",
)
assert_status(resp, 201, "create cliente")
cliente_id = resp.data["nit"]
print("[OK] Cliente creado", cliente_id)

print("[INFO] Listando clientes...")
resp = client.get("/api/clientes/")
assert_status(resp, 200, "list clientes")

print("[INFO] Actualizando cliente (PATCH)...")
resp = client.patch(
    f"/api/clientes/{cliente_id}/",
    {"direccion": "Zona 10"},
    format="json",
)
assert_status(resp, 200, "patch cliente")

print("[INFO] Creando vendedor...")
vendedor_dpi = str(random.randint(1000000000000, 9999999999999))
resp = client.post(
    "/api/vendedores/",
    {
        "dpi": vendedor_dpi,
        "nombre": "Vendedor API",
        "sueldo": "2500.00",
        "nivel_exito_porcent": 75,
    },
    format="json",
)
assert_status(resp, 201, "create vendedor")
print("[OK] Vendedor creado", vendedor_dpi)

print("[INFO] Creando producto...")
prod_code = f"PX{suffix}"
resp = client.post(
    "/api/productos/",
    {
        "codigo": prod_code,
        "descripcion": "Producto API",
        "color": "Rojo",
        "precio_unitario": "99.99",
        "presentacion_id": "INDIVIDUAL",
    },
    format="json",
)
assert_status(resp, 201, "create producto")
print("[OK] Producto creado", prod_code)

print("[INFO] Creando ruta...")
resp = client.post(
    "/api/rutas/",
    {
        "dpi_vendedor": vendedor_dpi,
    "fecha": timezone.now().date().isoformat(),
        "nombre": "Ruta Auto",
        "kilometros_estimados": "120.5",
        "tiempo_planificado_min": 180,
    },
    format="json",
)
assert_status(resp, 201, "create ruta")
ruta_id = resp.data["id_ruta"]
print("[OK] Ruta creada", ruta_id)

# Ensure ClienteRuta exists for comparacion endpoint
time_catalog = CatTiempoCliente.objects.first()
if time_catalog:
    ClienteRuta.objects.get_or_create(
        ruta_id=ruta_id,
        cliente_id=cliente_id,
        defaults={
            "orden_visita": 1,
            "id_tiempo_cliente": time_catalog,
            "resultado_visita_id": "PENDIENTE",
        },
    )

print("[INFO] Creando venta via rutas/{id}/recorridos/ ...")
resp = client.post(
    f"/api/rutas/{ruta_id}/recorridos/",
    {
        "fecha": timezone.now().isoformat(),
        "nit_cliente": cliente_id,
        "total": "150.00",
        "creado_en": timezone.now().isoformat(),
        "actualizado_en": timezone.now().isoformat(),
    },
    format="json",
)
assert_status(resp, 201, "create venta en recorrido")
venta_id = resp.data["id_venta"]
print("[OK] Venta creada", venta_id)

print("[INFO] Consultando recorridos...")
resp = client.get(f"/api/rutas/{ruta_id}/recorridos/")
assert_status(resp, 200, "list recorridos")

print("[INFO] Consultando comparacion_tiempos...")
resp = client.get(f"/api/rutas/{ruta_id}/comparacion_tiempos/")
assert_status(resp, 200, "comparacion tiempos")

print("[INFO] Generando reportes PDF...")
report_requests = [
    ("clientes", {}),
    ("productos", {}),
    ("vendedores", {}),
    ("rutas", {}),
    ("ventas", {"desde": "2024-01-01"}),
    ("historial", {"desde": "2024-01-01"}),
    ("comparacion", {}),
]

generated_reports = []
for tipo, filtros in report_requests:
    resp = client.post(
        "/api/reportes/",
        {
            "tipo": tipo,
            "filtros": filtros,
        },
        format="json",
    )
    assert_status(resp, 200, f"crear reporte {tipo}")
    uid = resp.data["uuid"]
    generated_reports.append(uid)
    print(f"[OK] Reporte {tipo} generado {uid}")

print("[INFO] Descargando primer reporte generado...")
resp = client.get(f"/api/reportes/descargar/{generated_reports[0]}/")
assert_status(resp, 200, "descargar primer reporte")

print("[INFO] Verificando vendedores list...")
resp = client.get("/api/vendedores/")
assert_status(resp, 200, "list vendedores")

print("[INFO] Verificando productos list...")
resp = client.get("/api/productos/")
assert_status(resp, 200, "list productos")

print("[INFO] Verificando rutas list...")
resp = client.get("/api/rutas/")
assert_status(resp, 200, "list rutas")

print("[INFO] Importando clientes via CSV...")
csv_nit = str(random.randint(200000000, 299999999))
csv_content = (
    "nit,nombre,direccion,correo_electronico,estatus_credito\n"
    f"{csv_nit},Cliente CSV Import,Calzada Aguilar Batres 1-01,import{csv_nit}@example.com,A\n"
)
uploaded = SimpleUploadedFile(
    "clientes_import.csv",
    csv_content.encode("utf-8"),
    content_type="text/csv",
)
resp = client.post(
    "/api/importaciones/clientes/csv/",
    {"archivo": uploaded},
    format="multipart",
)
assert_status(resp, 201, "import clientes csv")
print("[OK] Importacion CSV completada")

print("[INFO] Verificando cliente importado...")
resp = client.get(f"/api/clientes/?n={csv_nit}")
assert_status(resp, 200, "buscar cliente importado")
if isinstance(resp.data, dict) and resp.data.get('results') is not None:
    clientes = resp.data['results']
else:
    clientes = resp.data
if not any(cliente.get('nit') == csv_nit for cliente in clientes):
    print(f"[FAIL] Cliente importado {csv_nit} no encontrado")
    sys.exit(1)
print("[OK] Cliente importado localizado")

print("[INFO] Registrando evidencia fotografica...")
resp = client.post(
    "/api/evidencias/",
    {
        "url": "https://picsum.photos/seed/api-smoke/800/600",
        "descripcion": "Evidencia generada por pruebas automáticas",
        "cliente": cliente_id,
        "ruta": ruta_id,
        "venta": venta_id,
    },
    format="json",
)
assert_status(resp, 201, "crear evidencia")
evidencia_id = resp.data["id"]
if not (resp.data.get("imagen_url") or resp.data.get("url")):
    print("[FAIL] Respuesta de creación sin URL de imagen")
    sys.exit(1)
print("[OK] Evidencia creada", evidencia_id)

print("[INFO] Listando evidencias por cliente...")
resp = client.get(f"/api/evidencias/?nit_cliente={cliente_id}")
assert_status(resp, 200, "listar evidencias")
if isinstance(resp.data, dict) and resp.data.get('results') is not None:
    evidencias = resp.data['results']
else:
    evidencias = resp.data
if not any(item.get('id') == evidencia_id for item in evidencias):
    print(f"[FAIL] Evidencia {evidencia_id} no devuelta en listado")
    sys.exit(1)
print("[OK] Evidencia encontrada en listado")

print("[INFO] Subiendo evidencia desde archivo...")
uploaded_photo = SimpleUploadedFile(
    "evidencia.png",
    PNG_SAMPLE,
    content_type="image/png",
)
resp = client.post(
    "/api/evidencias/subir/",
    {
        "archivo": uploaded_photo,
        "descripcion": "Foto subida por pruebas",
        "cliente": cliente_id,
        "ruta": ruta_id,
        "venta": venta_id,
    },
    format="multipart",
)
assert_status(resp, 201, "subir evidencia")
uploaded_url = resp.data.get("imagen_url")
if not uploaded_url:
    print("[FAIL] Respuesta de upload sin imagen_url")
    sys.exit(1)
print("[OK] Evidencia subida con URL", uploaded_url)

print("[SUCCESS] API smoke tests completed successfully")