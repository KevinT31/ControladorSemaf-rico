"""
Exportador a Azure Blob Storage

Este módulo exporta resultados de procesamiento de videos a Azure Cloud:
- Videos procesados
- CSVs de métricas
- JSONs de estadísticas
- Gráficos de análisis

Requisitos:
    pip install azure-storage-blob python-dotenv

Configuración:
    Crear archivo .env con:
    AZURE_STORAGE_CONNECTION_STRING=your_connection_string
    AZURE_STORAGE_CONTAINER_NAME=trafico-lima

Uso:
    python exportador_azure.py --directorio datos/resultados-video/exportaciones/parametros/
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import json

logger = logging.getLogger(__name__)

try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("azure-storage-blob no instalado. Instalar con: pip install azure-storage-blob")

try:
    from dotenv import load_dotenv
    load_dotenv()  # Cargar variables de .env
except ImportError:
    logger.warning("python-dotenv no instalado. Variables de entorno deben estar configuradas manualmente")


class ExportadorAzure:
    """
    Exportador de resultados a Azure Blob Storage
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        container_name: Optional[str] = None
    ):
        """
        Args:
            connection_string: Connection string de Azure Storage
                              Si es None, se lee de variable de entorno AZURE_STORAGE_CONNECTION_STRING
            container_name: Nombre del container
                           Si es None, se lee de variable de entorno AZURE_STORAGE_CONTAINER_NAME
        """
        if not AZURE_AVAILABLE:
            raise ImportError("azure-storage-blob no instalado. Instalar con: pip install azure-storage-blob")

        # Obtener credenciales
        self.connection_string = connection_string or os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.container_name = container_name or os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'trafico-lima')

        if not self.connection_string:
            raise ValueError(
                "Connection string no proporcionado. "
                "Definir AZURE_STORAGE_CONNECTION_STRING en .env o pasar como parámetro"
            )

        # Crear cliente
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)

            # Crear container si no existe
            try:
                self.container_client.get_container_properties()
                logger.info(f"✓ Conectado a container: {self.container_name}")
            except Exception:
                self.container_client.create_container()
                logger.info(f"✓ Container creado: {self.container_name}")

        except Exception as e:
            logger.error(f"Error conectando a Azure: {e}")
            raise

    def subir_archivo(
        self,
        ruta_local: str,
        ruta_blob: Optional[str] = None,
        sobrescribir: bool = True,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Sube un archivo a Azure Blob Storage

        Args:
            ruta_local: Ruta al archivo local
            ruta_blob: Ruta en el blob (si es None, usa nombre del archivo)
            sobrescribir: Si sobrescribir archivo existente
            metadata: Metadata adicional para el blob

        Returns:
            URL del blob subido
        """
        ruta_local = Path(ruta_local)

        if not ruta_local.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_local}")

        # Determinar nombre del blob
        if ruta_blob is None:
            # Usar estructura: año/mes/día/archivo
            fecha_hoy = datetime.now()
            ruta_blob = f"{fecha_hoy.year}/{fecha_hoy.month:02d}/{fecha_hoy.day:02d}/{ruta_local.name}"

        blob_client = self.container_client.get_blob_client(ruta_blob)

        # Determinar content type
        content_type = self._obtener_content_type(ruta_local.suffix)
        content_settings = ContentSettings(content_type=content_type)

        # Metadata por defecto
        if metadata is None:
            metadata = {}

        metadata.update({
            'upload_timestamp': datetime.now().isoformat(),
            'original_filename': ruta_local.name,
            'file_size_bytes': str(ruta_local.stat().st_size)
        })

        try:
            with open(ruta_local, 'rb') as data:
                blob_client.upload_blob(
                    data,
                    overwrite=sobrescribir,
                    content_settings=content_settings,
                    metadata=metadata
                )

            url = blob_client.url
            logger.info(f"✓ Archivo subido: {ruta_local.name} → {ruta_blob}")
            return url

        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            raise

    def subir_directorio(
        self,
        directorio_local: str,
        prefijo_blob: Optional[str] = None,
        incluir_subdirectorios: bool = True,
        patron: str = "*"
    ) -> List[str]:
        """
        Sube todos los archivos de un directorio a Azure

        Args:
            directorio_local: Directorio local a subir
            prefijo_blob: Prefijo para los blobs (e.g., "resultados/2025/")
            incluir_subdirectorios: Si incluir subdirectorios
            patron: Patrón de archivos a incluir (e.g., "*.mp4", "*.csv")

        Returns:
            Lista de URLs de blobs subidos
        """
        directorio = Path(directorio_local)

        if not directorio.exists() or not directorio.is_dir():
            raise ValueError(f"Directorio no válido: {directorio_local}")

        urls = []

        # Obtener archivos
        if incluir_subdirectorios:
            archivos = list(directorio.rglob(patron))
        else:
            archivos = list(directorio.glob(patron))

        logger.info(f"Subiendo {len(archivos)} archivos de {directorio.name}...")

        for archivo in archivos:
            if archivo.is_file():
                # Mantener estructura de directorios
                ruta_relativa = archivo.relative_to(directorio)

                if prefijo_blob:
                    ruta_blob = f"{prefijo_blob}/{ruta_relativa}"
                else:
                    fecha_hoy = datetime.now()
                    ruta_blob = f"{fecha_hoy.year}/{fecha_hoy.month:02d}/{fecha_hoy.day:02d}/{directorio.name}/{ruta_relativa}"

                ruta_blob = str(ruta_blob).replace('\\', '/')  # Azure usa /

                try:
                    url = self.subir_archivo(str(archivo), ruta_blob)
                    urls.append(url)
                except Exception as e:
                    logger.error(f"Error subiendo {archivo.name}: {e}")

        logger.info(f"✓ {len(urls)}/{len(archivos)} archivos subidos exitosamente")

        return urls

    def listar_blobs(self, prefijo: Optional[str] = None) -> List[str]:
        """
        Lista blobs en el container

        Args:
            prefijo: Filtrar por prefijo (e.g., "2025/01/")

        Returns:
            Lista de nombres de blobs
        """
        blobs = self.container_client.list_blobs(name_starts_with=prefijo)
        return [blob.name for blob in blobs]

    def descargar_blob(self, nombre_blob: str, ruta_destino: str):
        """
        Descarga un blob de Azure

        Args:
            nombre_blob: Nombre del blob en Azure
            ruta_destino: Ruta local donde guardar
        """
        blob_client = self.container_client.get_blob_client(nombre_blob)

        Path(ruta_destino).parent.mkdir(parents=True, exist_ok=True)

        with open(ruta_destino, 'wb') as f:
            download_stream = blob_client.download_blob()
            f.write(download_stream.readall())

        logger.info(f"✓ Blob descargado: {nombre_blob} → {ruta_destino}")

    def eliminar_blob(self, nombre_blob: str):
        """
        Elimina un blob

        Args:
            nombre_blob: Nombre del blob a eliminar
        """
        blob_client = self.container_client.get_blob_client(nombre_blob)
        blob_client.delete_blob()
        logger.info(f"✓ Blob eliminado: {nombre_blob}")

    def generar_url_sas(
        self,
        nombre_blob: str,
        expiracion_horas: int = 24
    ) -> str:
        """
        Genera URL con SAS token (acceso temporal)

        Args:
            nombre_blob: Nombre del blob
            expiracion_horas: Horas hasta que expire el link

        Returns:
            URL con SAS token
        """
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from datetime import timedelta

        blob_client = self.container_client.get_blob_client(nombre_blob)

        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=self.container_name,
            blob_name=nombre_blob,
            account_key=blob_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiracion_horas)
        )

        url_con_sas = f"{blob_client.url}?{sas_token}"
        return url_con_sas

    @staticmethod
    def _obtener_content_type(extension: str) -> str:
        """Obtiene content type según extensión"""
        content_types = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.pdf': 'application/pdf'
        }

        return content_types.get(extension.lower(), 'application/octet-stream')


def exportar_resultados_a_azure(
    directorio_local: str,
    modo: str = "parametros"
) -> Dict:
    """
    Función helper para exportar resultados de procesamiento a Azure

    Args:
        directorio_local: Directorio con resultados (e.g., datos/resultados-video/exportaciones/parametros/)
        modo: Modo de procesamiento (deteccion/parametros/emergencia)

    Returns:
        Diccionario con estadísticas de exportación
    """
    try:
        exportador = ExportadorAzure()

        # Crear prefijo organizado
        fecha_hoy = datetime.now()
        prefijo = f"resultados/{fecha_hoy.year}/{fecha_hoy.month:02d}/{fecha_hoy.day:02d}/{modo}"

        # Subir todos los archivos
        urls = exportador.subir_directorio(
            directorio_local=directorio_local,
            prefijo_blob=prefijo,
            incluir_subdirectorios=True
        )

        # Crear manifiesto
        manifiesto = {
            'fecha_exportacion': datetime.now().isoformat(),
            'modo': modo,
            'directorio_local': directorio_local,
            'archivos_subidos': len(urls),
            'urls': urls
        }

        # Guardar manifiesto localmente
        ruta_manifiesto = Path(directorio_local) / 'manifiesto_azure.json'
        with open(ruta_manifiesto, 'w', encoding='utf-8') as f:
            json.dump(manifiesto, f, indent=2, ensure_ascii=False)

        # Subir manifiesto
        exportador.subir_archivo(
            str(ruta_manifiesto),
            f"{prefijo}/manifiesto.json"
        )

        logger.info("✓ Exportación a Azure completada")
        logger.info(f"  Archivos subidos: {len(urls)}")
        logger.info(f"  Ubicación: {prefijo}")

        return manifiesto

    except Exception as e:
        logger.error(f"Error exportando a Azure: {e}")
        return {'error': str(e)}


# Ejemplo de uso
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Exportador de resultados a Azure Blob Storage')

    parser.add_argument(
        '--directorio',
        type=str,
        required=True,
        help='Directorio local con resultados a subir'
    )

    parser.add_argument(
        '--modo',
        type=str,
        default='parametros',
        choices=['deteccion', 'parametros', 'emergencia'],
        help='Modo de procesamiento'
    )

    args = parser.parse_args()

    # Verificar .env
    if not os.getenv('AZURE_STORAGE_CONNECTION_STRING'):
        print("⚠️ ADVERTENCIA: Variable AZURE_STORAGE_CONNECTION_STRING no definida")
        print("")
        print("Crear archivo .env en la raíz del proyecto con:")
        print("")
        print("AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net")
        print("AZURE_STORAGE_CONTAINER_NAME=trafico-lima")
        print("")
        print("Obtener connection string desde Azure Portal:")
        print("  Storage Account → Access keys → Connection string")
        print("")
        exit(1)

    # Exportar
    resultado = exportar_resultados_a_azure(args.directorio, args.modo)

    if 'error' in resultado:
        print(f"❌ Error: {resultado['error']}")
        exit(1)
    else:
        print("\n" + "=" * 70)
        print("EXPORTACIÓN COMPLETADA")
        print("=" * 70)
        print(f"Archivos subidos: {resultado['archivos_subidos']}")
        print(f"Fecha: {resultado['fecha_exportacion']}")
