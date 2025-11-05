from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Cliente, Producto, Venta, DetalleVenta, Vendedor, RegistroVisita,
    Ruta, ClienteRuta, CatPresentacion, CatEstatusCredito, ReportFile, UserProfile,
    EvidenciaFotografica,
)


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'


class VentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venta
        fields = ['id_venta', 'fecha', 'nit_cliente', 'id_ruta', 'total', 'creado_en', 'actualizado_en']


class DetalleVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleVenta
        fields = '__all__'


# Serializer de productos que traduce entre el id de presentación y su nombre.
class ProductoSerializer(serializers.ModelSerializer):
    presentacion = serializers.CharField(source='presentacion.presentacion', read_only=True)
    presentacion_id = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Producto
        fields = ['codigo', 'descripcion', 'color', 'precio_unitario', 'presentacion', 'presentacion_id', 'creado_en', 'actualizado_en']

    def create(self, validated_data):
        presentacion_value = validated_data.pop('presentacion_id')
        validated_data['presentacion'] = CatPresentacion.objects.get(presentacion=presentacion_value)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'presentacion_id' in validated_data:
            presentacion_value = validated_data.pop('presentacion_id')
            instance.presentacion = CatPresentacion.objects.get(presentacion=presentacion_value)
        return super().update(instance, validated_data)


# Incluimos los datos del cliente dentro de la ruta para no hacer consultas extra.
class ClienteRutaSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)

    class Meta:
        model = ClienteRuta
        fields = ['ruta', 'cliente', 'orden_visita', 'id_tiempo_cliente', 'hora_inicio', 'hora_fin', 'resultado_visita', 'observaciones']


# Rutas con sus clientes ya ordenados.
class RutaSerializer(serializers.ModelSerializer):
    clienterutas = ClienteRutaSerializer(source='clienteruta_set', many=True, read_only=True)

    class Meta:
        model = Ruta
        fields = ['id_ruta', 'dpi_vendedor', 'fecha', 'nombre', 'kilometros_estimados', 'tiempo_planificado_min', 'tiempo_real_min', 'resultado_global', 'clienterutas']


# Vendedores incluyen un resumen textual del nivel de éxito.
class VendedorSerializer(serializers.ModelSerializer):
    nivel_exito = serializers.SerializerMethodField()

    class Meta:
        model = Vendedor
        fields = ['dpi', 'nombre', 'correo_electronico', 'telefono', 'sueldo', 'nivel_exito_porcent', 'nivel_exito', 'creado_en', 'actualizado_en']

    def get_nivel_exito(self, obj):
        p = obj.nivel_exito_porcent
        if p is None:
            return None
        if p >= 70:
            return 'alto'
        if p >= 40:
            return 'medio'
        return 'bajo'


class RegistroVisitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroVisita
        fields = '__all__'


# Serializador de evidencias que expone datos relacionados listos para el frontend.
class EvidenciaFotograficaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    ruta_nombre = serializers.CharField(source='ruta.nombre', read_only=True)
    venta_total = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = EvidenciaFotografica
        fields = [
            'id',
            'imagen',
            'imagen_url',
            'url',
            'descripcion',
            'cliente',
            'cliente_nombre',
            'ruta',
            'ruta_nombre',
            'venta',
            'venta_total',
            'registrada_en',
        ]
        extra_kwargs = {
            'imagen': {'write_only': True, 'required': False},
            'url': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def validate(self, attrs):
        imagen = attrs.get('imagen')
        url = attrs.get('url')
        instance = getattr(self, 'instance', None)
        has_existing_media = False
        if instance is not None:
            has_existing_media = bool(getattr(instance, 'imagen')) or bool(getattr(instance, 'url'))
        if not imagen and (url is None or url == '') and not has_existing_media:
            raise serializers.ValidationError('Debe proporcionar una imagen o un URL de evidencia.')
        return attrs

    def get_imagen_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        if obj.imagen and hasattr(obj.imagen, 'url'):
            url = obj.imagen.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return obj.url

    def get_venta_total(self, obj):
        if obj.venta:
            return obj.venta.total
        return None


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


# Juntamos perfil y datos del usuario para simplificar la respuesta en APIs.
class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = ['user', 'rol']


class ReportFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportFile
        fields = '__all__'
