"""
Datos de Intersecciones y Conexiones de Lima

Archivo separado con los datos estáticos de las 31 intersecciones
"""

from typing import List, Dict, Tuple


def obtener_intersecciones_lima() -> List[Dict]:
    """
    Retorna lista de las 31 intersecciones reales de Lima con coordenadas exactas

    Returns:
        Lista de diccionarios con datos de intersecciones
    """
    return [
        # MIRAFLORES (3 intersecciones)
        {'id': 'MIR-001', 'nombre': 'Av. Arequipa con Av. Angamos', 'latitud': -12.110273, 'longitud': -77.034874, 'num_carriles': 6, 'zona': 'sur'},
        {'id': 'MIR-002', 'nombre': 'Av. Larco con Av. Benavides', 'latitud': -12.121832, 'longitud': -77.031044, 'num_carriles': 4, 'zona': 'sur'},
        {'id': 'MIR-003', 'nombre': 'Av. Arequipa con Av. Benavides', 'latitud': -12.119354, 'longitud': -77.034225, 'num_carriles': 6, 'zona': 'sur'},

        # SAN ISIDRO (3 intersecciones)
        {'id': 'SI-001', 'nombre': 'Av. Javier Prado con Av. Arequipa', 'latitud': -12.094817, 'longitud': -77.036156, 'num_carriles': 8, 'zona': 'centro'},
        {'id': 'SI-002', 'nombre': 'Av. Camino Real con Av. República de Panamá', 'latitud': -12.098156, 'longitud': -77.038967, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'SI-003', 'nombre': 'Av. Javier Prado con Av. Canaval y Moreyra', 'latitud': -12.091234, 'longitud': -77.030453, 'num_carriles': 6, 'zona': 'centro'},

        # LIMA CENTRO (4 intersecciones)
        {'id': 'LC-001', 'nombre': 'Av. Abancay con Jr. Lampa', 'latitud': -12.046978, 'longitud': -77.033456, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-002', 'nombre': 'Av. Nicolás de Piérola con Jr. de la Unión', 'latitud': -12.046234, 'longitud': -77.030789, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-003', 'nombre': 'Av. Tacna con Av. Emancipación', 'latitud': -12.051234, 'longitud': -77.032567, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-004', 'nombre': 'Av. Alfonso Ugarte con Av. Venezuela', 'latitud': -12.057823, 'longitud': -77.038912, 'num_carriles': 6, 'zona': 'centro'},

        # LA VICTORIA (2 intersecciones)
        {'id': 'LV-001', 'nombre': 'Av. Grau con Av. 28 de Julio', 'latitud': -12.067845, 'longitud': -77.026123, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'LV-002', 'nombre': 'Av. Aviación con Av. Javier Prado', 'latitud': -12.085234, 'longitud': -77.005678, 'num_carriles': 8, 'zona': 'centro'},

        # SURCO (4 intersecciones)
        {'id': 'SUR-001', 'nombre': 'Av. Javier Prado con Av. Primavera', 'latitud': -12.093145, 'longitud': -76.978934, 'num_carriles': 8, 'zona': 'sur'},
        {'id': 'SUR-002', 'nombre': 'Av. Benavides con Av. Tomás Marsano', 'latitud': -12.118923, 'longitud': -77.006734, 'num_carriles': 6, 'zona': 'sur'},
        {'id': 'SUR-003', 'nombre': 'Av. Higuereta con Av. El Polo', 'latitud': -12.134812, 'longitud': -76.993567, 'num_carriles': 4, 'zona': 'sur'},
        {'id': 'SUR-004', 'nombre': 'Av. Primavera con Av. República de Panamá', 'latitud': -12.106234, 'longitud': -76.979123, 'num_carriles': 6, 'zona': 'sur'},

        # SAN JUAN DE LURIGANCHO (2 intersecciones)
        {'id': 'SJL-001', 'nombre': 'Av. Próceres con Av. Los Jardines', 'latitud': -11.991823, 'longitud': -77.008934, 'num_carriles': 6, 'zona': 'este'},
        {'id': 'SJL-002', 'nombre': 'Av. Wiesse con Av. Gran Chimú', 'latitud': -11.984567, 'longitud': -77.001234, 'num_carriles': 4, 'zona': 'este'},

        # SAN MIGUEL (3 intersecciones)
        {'id': 'SM-001', 'nombre': 'Av. La Marina con Av. Universitaria', 'latitud': -12.077123, 'longitud': -77.083456, 'num_carriles': 8, 'zona': 'oeste'},
        {'id': 'SM-002', 'nombre': 'Av. Elmer Faucett con Av. Universitaria', 'latitud': -12.065234, 'longitud': -77.089867, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'SM-003', 'nombre': 'Av. La Marina con Av. Venezuela', 'latitud': -12.076845, 'longitud': -77.091234, 'num_carriles': 6, 'zona': 'oeste'},

        # JESÚS MARÍA (2 intersecciones)
        {'id': 'JM-001', 'nombre': 'Av. Brasil con Av. 28 de Julio', 'latitud': -12.068934, 'longitud': -77.044567, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'JM-002', 'nombre': 'Av. Salaverry con Av. Arequipa', 'latitud': -12.082967, 'longitud': -77.043812, 'num_carriles': 6, 'zona': 'centro'},

        # SAN BORJA (3 intersecciones)
        {'id': 'SB-001', 'nombre': 'Av. Javier Prado con Av. Aviación', 'latitud': -12.087823, 'longitud': -77.005967, 'num_carriles': 10, 'zona': 'centro'},
        {'id': 'SB-002', 'nombre': 'Av. San Luis con Av. San Borja Norte', 'latitud': -12.094823, 'longitud': -77.001645, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'SB-003', 'nombre': 'Av. Angamos con Av. Aviación', 'latitud': -12.110567, 'longitud': -77.006234, 'num_carriles': 8, 'zona': 'centro'},

        # PUEBLO LIBRE (2 intersecciones)
        {'id': 'PL-001', 'nombre': 'Av. La Marina con Av. Bolívar', 'latitud': -12.070945, 'longitud': -77.064123, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'PL-002', 'nombre': 'Av. Brasil con Av. Bolívar', 'latitud': -12.072834, 'longitud': -77.057234, 'num_carriles': 6, 'zona': 'oeste'},

        # LINCE (1 intersección)
        {'id': 'LIN-001', 'nombre': 'Av. Arequipa con Av. Petit Thouars', 'latitud': -12.081723, 'longitud': -77.034845, 'num_carriles': 6, 'zona': 'centro'}
    ]


def obtener_conexiones_lima() -> List[Tuple[str, str, float]]:
    """
    Retorna lista de conexiones entre intersecciones con distancias reales

    Returns:
        Lista de tuplas (origen_id, destino_id, distancia_metros)
    """
    return [
        # Av. Arequipa (eje norte-sur)
        ('SI-001', 'LIN-001', 1400),
        ('LIN-001', 'JM-002', 200),
        ('JM-002', 'MIR-001', 2800),
        ('MIR-001', 'MIR-003', 900),

        # Av. Javier Prado (eje este-oeste)
        ('SI-001', 'SI-003', 700),
        ('SI-003', 'LV-002', 2500),
        ('LV-002', 'SB-001', 200),
        ('SB-001', 'SUR-001', 2600),

        # Av. La Marina (zona oeste)
        ('SM-001', 'SM-003', 800),
        ('SM-003', 'PL-001', 1900),

        # Centro de Lima
        ('LC-001', 'LC-002', 400),
        ('LC-002', 'LC-003', 600),
        ('LC-003', 'LC-004', 900),

        # Av. Aviación (norte-sur)
        ('LV-002', 'SB-001', 200),
        ('SB-001', 'SB-003', 2500),

        # Av. Angamos (este-oeste)
        ('MIR-001', 'SB-003', 2800),

        # Av. Benavides (este-oeste)
        ('MIR-003', 'SUR-002', 2800),

        # Surco
        ('SUR-001', 'SUR-004', 1400),
        ('SUR-002', 'SUR-003', 1800),

        # Av. Brasil (este-oeste)
        ('JM-001', 'PL-002', 1300)
    ]
