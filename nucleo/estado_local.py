"""
Sistema de Estado Local para Control Semafórico Adaptativo
Implementa todas las variables y funciones descritas en la Sección 6.2 del Capítulo 6

Componentes principales:
- CamMask: Control de orientación de cámara
- Variables de entrada: SC, Vavg, q, k, ICV, PI, EV
- Matriz de estado local normalizada
- Tracking de vehículos de emergencia
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class VehiculoEmergencia:
    """Estado completo de un vehículo de emergencia"""
    id_tracking: int
    clase: str  # 'ambulancia', 'bomberos', 'policia'
    pos_x: float  # Posición X en metros
    pos_y: float  # Posición Y en metros
    vel_x: float  # Velocidad X en m/s
    vel_y: float  # Velocidad Y en m/s
    direccion_inicial: str  # 'N', 'S', 'E', 'O'
    direccion_salida: Optional[str] = None  # Dirección predicha de salida
    confidence: float = 0.0  # Confianza de la detección
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ParametrosInterseccion:
    """Parámetros de configuración de una intersección"""
    # Valores máximos para normalización
    SC_MAX: float = 40.0  # Máximo número de vehículos detenidos observable
    V_MAX: float = 60.0  # Velocidad máxima (km/h)
    V_MIN: float = 0.0
    Q_MAX: float = 30.0  # Flujo máximo (veh/min)
    Q_MIN: float = 0.0
    K_MAX: float = 0.15  # Densidad máxima (veh/m)
    K_MIN: float = 0.0

    # Umbrales
    EPSILON_VELOCIDAD: float = 5.0  # km/h - umbral para vehículo detenido
    EV_CONFIDENCE_THRESHOLD: float = 0.7  # Umbral de confianza para emergencia

    # Geometría de intersección
    LONGITUD_EFECTIVA: float = 100.0  # Longitud efectiva del área visible (m)
    RADIO_COBERTURA: float = 50.0  # Radio de cobertura de cámara (m)
    R_TRIGGER: float = 30.0  # Radio de activación de cambio de cámara (m)
    CENTROIDE_X: float = 0.0  # Centroide de la intersección
    CENTROIDE_Y: float = 0.0

    # Pesos para ICV
    W1_SC: float = 0.30  # Peso de cola
    W2_V: float = 0.25  # Peso de velocidad
    W3_K: float = 0.25  # Peso de densidad
    W4_Q: float = 0.20  # Peso de flujo

    def __post_init__(self):
        """Valida que los pesos sumen 1"""
        suma_pesos = self.W1_SC + self.W2_V + self.W3_K + self.W4_Q
        if not np.isclose(suma_pesos, 1.0):
            logger.warning(f"Los pesos ICV suman {suma_pesos}, normalizando...")
            factor = 1.0 / suma_pesos
            self.W1_SC *= factor
            self.W2_V *= factor
            self.W3_K *= factor
            self.W4_Q *= factor


class EstadoLocalInterseccion:
    """
    Gestiona el estado local completo de una intersección
    Implementa todas las funciones y variables de la Sección 6.2
    """

    def __init__(self,
                 id_interseccion: str,
                 params: Optional[ParametrosInterseccion] = None):
        """
        Args:
            id_interseccion: Identificador único de la intersección
            params: Parámetros de configuración (usa valores por defecto si None)
        """
        self.id = id_interseccion
        self.params = params or ParametrosInterseccion()

        # CamMask: Estado de orientación de cámara
        # 0 = Este-Oeste (EO), 1 = Norte-Sur (NS)
        self.cam_mask: int = 0

        # Direcciones posibles
        self.direcciones = ['N', 'S', 'E', 'O']

        # Matrices de estado por dirección [N, S, E, O]
        self.SC = np.zeros(4, dtype=float)  # Stopped Count - vehículos detenidos
        self.Vavg = np.zeros(4, dtype=float)  # Velocidad promedio (km/h)
        self.q = np.zeros(4, dtype=float)  # Flujo vehicular (veh/min)
        self.k = np.zeros(4, dtype=float)  # Densidad (veh/m)
        self.ICV = np.zeros(4, dtype=float)  # Índice de Congestión Vehicular
        self.PI = np.zeros(4, dtype=float)  # Parámetro de Intensidad
        self.EV = np.zeros(4, dtype=float)  # Emergency Vehicles count

        # Historial para cálculo de flujo
        self.historial_cruces = {d: [] for d in self.direcciones}
        self.ventana_tiempo_flujo = 60.0  # segundos

        # Tracking de vehículos de emergencia
        self.vehiculos_emergencia: List[VehiculoEmergencia] = []

        # Timestamp de última actualización
        self.timestamp = datetime.now()

        # Matriz de estado normalizada (7 filas x 4 columnas) para transmisión
        self.matriz_estado_normalizada = np.zeros((7, 4), dtype=float)

    def actualizar_cam_mask(self, nuevo_valor: int):
        """
        Actualiza la orientación de la cámara

        Args:
            nuevo_valor: 0 para EO, 1 para NS
        """
        if nuevo_valor not in [0, 1]:
            raise ValueError("CamMask debe ser 0 (EO) o 1 (NS)")

        old_mask = self.cam_mask
        self.cam_mask = nuevo_valor

        if old_mask != nuevo_valor:
            logger.info(f"[{self.id}] CamMask cambiado: "
                       f"{'EO' if old_mask == 0 else 'NS'} → "
                       f"{'EO' if nuevo_valor == 0 else 'NS'}")

    def calcular_stopped_count(self,
                               vehiculos_detectados: List[Dict],
                               direccion: str) -> float:
        """
        Calcula el conteo de vehículos detenidos en una dirección

        Función: StoppedCount(l,t) = Σ I_v donde I_v = 1 si velocidad(v) < ε

        Args:
            vehiculos_detectados: Lista de diccionarios con info de vehículos
                                 Formato: {'id': int, 'velocidad': float, 'clase': str, ...}
            direccion: 'N', 'S', 'E', 'O'

        Returns:
            Número de vehículos detenidos
        """
        if not vehiculos_detectados:
            return 0.0

        count = 0
        for veh in vehiculos_detectados:
            velocidad_kmh = veh.get('velocidad', 0.0)
            if velocidad_kmh < self.params.EPSILON_VELOCIDAD:
                count += 1

        return float(count)

    def calcular_velocidad_promedio(self,
                                    vehiculos_detectados: List[Dict],
                                    direccion: str) -> float:
        """
        Calcula la velocidad promedio de vehículos en movimiento

        Función: Vavg(l,t) = (1/N_mov) Σ velocidad(v) para v en V_mov
        donde V_mov = {v ∈ V : velocidad(v) >= ε}

        Args:
            vehiculos_detectados: Lista de vehículos
            direccion: Dirección del carril

        Returns:
            Velocidad promedio en km/h (0 si no hay vehículos en movimiento)
        """
        if not vehiculos_detectados:
            return 0.0

        velocidades_mov = [
            v['velocidad'] for v in vehiculos_detectados
            if v.get('velocidad', 0.0) >= self.params.EPSILON_VELOCIDAD
        ]

        if not velocidades_mov:
            return 0.0

        return float(np.mean(velocidades_mov))

    def calcular_flujo_vehicular(self,
                                 vehiculos_que_cruzaron: int,
                                 direccion: str,
                                 tiempo_transcurrido: float = None) -> float:
        """
        Calcula el flujo vehicular (vehículos por minuto)

        Función: q(l,t) = N_cross(l, t0, t) / (t - t0)

        Args:
            vehiculos_que_cruzaron: Número de vehículos que cruzaron la línea
            direccion: Dirección del carril
            tiempo_transcurrido: Tiempo en segundos (usa ventana por defecto si None)

        Returns:
            Flujo en vehículos/minuto
        """
        if tiempo_transcurrido is None:
            tiempo_transcurrido = self.ventana_tiempo_flujo

        if tiempo_transcurrido <= 0:
            return 0.0

        # Convertir a veh/min
        flujo_por_segundo = vehiculos_que_cruzaron / tiempo_transcurrido
        flujo_por_minuto = flujo_por_segundo * 60.0

        return float(flujo_por_minuto)

    def calcular_densidad_vehicular(self,
                                    vehiculos_detectados: List[Dict],
                                    direccion: str) -> float:
        """
        Calcula la densidad vehicular espacial

        Función: k(l,t) = N_total(l,t) / L_efectiva

        Args:
            vehiculos_detectados: Lista de vehículos en el área visible
            direccion: Dirección del carril

        Returns:
            Densidad en vehículos/metro
        """
        n_total = len(vehiculos_detectados) if vehiculos_detectados else 0
        densidad = n_total / self.params.LONGITUD_EFECTIVA
        return float(densidad)

    def detectar_vehiculos_emergencia(self,
                                      vehiculos_detectados: List[Dict],
                                      direccion: str) -> float:
        """
        Detecta vehículos de emergencia (ambulancias, bomberos)

        Función: EV(l,t) = Σ I_emg(v,t)
        donde I_emg = 1 si class(v) ∈ C_emg AND confidence(v) >= θ_EV

        Args:
            vehiculos_detectados: Lista de vehículos con clasificación
            direccion: Dirección del carril

        Returns:
            Número de vehículos de emergencia detectados
        """
        clases_emergencia = {'ambulancia', 'ambulance', 'bomberos', 'fire_truck', 'policia', 'police'}

        count = 0
        for veh in vehiculos_detectados:
            clase = veh.get('clase', '').lower()
            confidence = veh.get('confidence', 0.0)

            if clase in clases_emergencia and confidence >= self.params.EV_CONFIDENCE_THRESHOLD:
                count += 1

                # Registrar en tracking si tiene info de posición
                if 'pos_x' in veh and 'pos_y' in veh:
                    veh_emg = VehiculoEmergencia(
                        id_tracking=veh.get('id', -1),
                        clase=clase,
                        pos_x=veh.get('pos_x', 0.0),
                        pos_y=veh.get('pos_y', 0.0),
                        vel_x=veh.get('vel_x', 0.0),
                        vel_y=veh.get('vel_y', 0.0),
                        direccion_inicial=direccion,
                        confidence=confidence
                    )
                    self._actualizar_tracking_emergencia(veh_emg)

        return float(count)

    def _actualizar_tracking_emergencia(self, veh_emg: VehiculoEmergencia):
        """
        Actualiza el tracking de vehículos de emergencia
        Predice dirección de salida y activa cambio de CamMask si necesario
        """
        # Buscar si ya existe en tracking
        existe = False
        for i, v in enumerate(self.vehiculos_emergencia):
            if v.id_tracking == veh_emg.id_tracking:
                self.vehiculos_emergencia[i] = veh_emg
                existe = True
                break

        if not existe:
            self.vehiculos_emergencia.append(veh_emg)
            logger.info(f"[{self.id}] Vehículo de emergencia detectado: {veh_emg.clase}")

        # Verificar si necesita cambio de CamMask (Zonas de activación crítica)
        self._verificar_cambio_cammask_emergencia(veh_emg)

    def _verificar_cambio_cammask_emergencia(self, veh_emg: VehiculoEmergencia):
        """
        Verifica si el vehículo de emergencia está en zona crítica que requiere
        cambio de orientación de cámara

        Zonas:
        - Z_NS→EO: |x - x_c| > R_trigger AND |x - x_c| < R
        - Z_EO→NS: |y - y_c| > R_trigger AND |y - y_c| < R
        """
        dx = abs(veh_emg.pos_x - self.params.CENTROIDE_X)
        dy = abs(veh_emg.pos_y - self.params.CENTROIDE_Y)

        R = self.params.RADIO_COBERTURA
        R_trig = self.params.R_TRIGGER

        # Zona que requiere vista EO (cámara en 0)
        en_zona_eo = (dx > R_trig and dx < R)

        # Zona que requiere vista NS (cámara en 1)
        en_zona_ns = (dy > R_trig and dy < R)

        if en_zona_eo and self.cam_mask != 0:
            logger.warning(f"[{self.id}] Vehículo emergencia en zona EO, cambiando CamMask...")
            self.actualizar_cam_mask(0)
        elif en_zona_ns and self.cam_mask != 1:
            logger.warning(f"[{self.id}] Vehículo emergencia en zona NS, cambiando CamMask...")
            self.actualizar_cam_mask(1)

    def calcular_icv(self, direccion: str) -> float:
        """
        Calcula el Índice de Congestión Vehicular para una dirección

        Función: ICV(l,t) = w1·(SC/SC_MAX) + w2·(1-Vavg/V_MAX) +
                           w3·(k/k_MAX) + w4·(1-q/q_MAX)

        Returns:
            ICV normalizado en [0,1]
        """
        idx = self.direcciones.index(direccion)

        # Componentes normalizadas
        comp_sc = self.SC[idx] / self.params.SC_MAX if self.params.SC_MAX > 0 else 0
        comp_v = 1.0 - (self.Vavg[idx] / self.params.V_MAX) if self.params.V_MAX > 0 else 0
        comp_k = self.k[idx] / self.params.K_MAX if self.params.K_MAX > 0 else 0
        comp_q = 1.0 - (self.q[idx] / self.params.Q_MAX) if self.params.Q_MAX > 0 else 0

        # Fórmula ICV
        icv = (self.params.W1_SC * comp_sc +
               self.params.W2_V * comp_v +
               self.params.W3_K * comp_k +
               self.params.W4_Q * comp_q)

        # Asegurar rango [0,1]
        icv = np.clip(icv, 0.0, 1.0)

        return float(icv)

    def calcular_parametro_intensidad(self, direccion: str, delta: float = 1e-6) -> float:
        """
        Calcula el Parámetro de Intensidad (PI)

        Función: PI(l,t) = Vavg(l,t) / (SC(l,t) + δ)

        Indica eficiencia: PI alto = flujo eficiente, PI bajo = congestión

        Returns:
            PI normalizado
        """
        idx = self.direcciones.index(direccion)

        # Evitar división por cero
        denominador = self.SC[idx] + delta

        pi = self.Vavg[idx] / denominador

        # Normalizar usando valores máximos esperados
        # PI_max teórico = V_MAX / delta (cuando SC=0)
        pi_max = self.params.V_MAX / delta
        pi_normalizado = pi / pi_max if pi_max > 0 else 0

        # Clip a [0,1]
        pi_normalizado = np.clip(pi_normalizado, 0.0, 1.0)

        return float(pi_normalizado)

    def actualizar_estado(self,
                         vehiculos_por_direccion: Dict[str, List[Dict]],
                         cruces_por_direccion: Dict[str, int] = None):
        """
        Actualiza todas las variables de estado basándose en detecciones actuales

        Args:
            vehiculos_por_direccion: Dict con listas de vehículos por dirección
                                    Formato: {'N': [{...}], 'S': [{...}], ...}
            cruces_por_direccion: Dict con conteo de cruces (para flujo)
        """
        self.timestamp = datetime.now()

        if cruces_por_direccion is None:
            cruces_por_direccion = {d: 0 for d in self.direcciones}

        for idx, direccion in enumerate(self.direcciones):
            vehiculos = vehiculos_por_direccion.get(direccion, [])
            cruces = cruces_por_direccion.get(direccion, 0)

            # Calcular variables según CamMask
            # Si cam_mask=0 (EO): solo actualizar E y O
            # Si cam_mask=1 (NS): solo actualizar N y S
            if self.cam_mask == 0:  # Vista EO
                if direccion in ['E', 'O']:
                    self.SC[idx] = self.calcular_stopped_count(vehiculos, direccion)
                    self.Vavg[idx] = self.calcular_velocidad_promedio(vehiculos, direccion)
                    self.q[idx] = self.calcular_flujo_vehicular(cruces, direccion)
                    self.k[idx] = self.calcular_densidad_vehicular(vehiculos, direccion)
                    self.EV[idx] = self.detectar_vehiculos_emergencia(vehiculos, direccion)
                # N y S mantienen valores anteriores
            else:  # Vista NS
                if direccion in ['N', 'S']:
                    self.SC[idx] = self.calcular_stopped_count(vehiculos, direccion)
                    self.Vavg[idx] = self.calcular_velocidad_promedio(vehiculos, direccion)
                    self.q[idx] = self.calcular_flujo_vehicular(cruces, direccion)
                    self.k[idx] = self.calcular_densidad_vehicular(vehiculos, direccion)
                    self.EV[idx] = self.detectar_vehiculos_emergencia(vehiculos, direccion)
                # E y O mantienen valores anteriores

            # Calcular ICV y PI siempre
            self.ICV[idx] = self.calcular_icv(direccion)
            self.PI[idx] = self.calcular_parametro_intensidad(direccion)

        # Actualizar matriz de estado normalizada
        self._construir_matriz_estado()

    def _construir_matriz_estado(self):
        """
        Construye la matriz de estado local normalizada (7x4)

        Formato:
        Fila 0: SC normalizado
        Fila 1: Vavg normalizado
        Fila 2: q normalizado
        Fila 3: k normalizado
        Fila 4: ICV (ya está normalizado)
        Fila 5: PI (ya está normalizado)
        Fila 6: EV (conteo)
        """
        # Normalizar cada variable
        sc_norm = self.SC / self.params.SC_MAX
        vavg_norm = (self.Vavg - self.params.V_MIN) / (self.params.V_MAX - self.params.V_MIN)
        q_norm = (self.q - self.params.Q_MIN) / (self.params.Q_MAX - self.params.Q_MIN)
        k_norm = (self.k - self.params.K_MIN) / (self.params.K_MAX - self.params.K_MIN)

        # Clip a [0,1]
        sc_norm = np.clip(sc_norm, 0, 1)
        vavg_norm = np.clip(vavg_norm, 0, 1)
        q_norm = np.clip(q_norm, 0, 1)
        k_norm = np.clip(k_norm, 0, 1)

        # Construir matriz
        self.matriz_estado_normalizada = np.array([
            sc_norm,
            vavg_norm,
            q_norm,
            k_norm,
            self.ICV,
            self.PI,
            self.EV
        ])

    def obtener_paquete_telemetria(self) -> Dict:
        """
        Genera el paquete de telemetría para transmisión

        Returns:
            Dict con toda la información de estado
        """
        paquete = {
            'intersection_id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'cam_mask': self.cam_mask,
            'state_matrix': {
                'SC': self.SC.tolist(),
                'Vavg': self.Vavg.tolist(),
                'q': self.q.tolist(),
                'k': self.k.tolist(),
                'ICV': self.ICV.tolist(),
                'PI': self.PI.tolist(),
                'EV': self.EV.tolist()
            },
            'state_matrix_normalized': self.matriz_estado_normalizada.tolist(),
            'emergency_vehicles': [
                {
                    'id': ev.id_tracking,
                    'clase': ev.clase,
                    'pos': [ev.pos_x, ev.pos_y],
                    'vel': [ev.vel_x, ev.vel_y],
                    'dir_inicial': ev.direccion_inicial,
                    'dir_salida': ev.direccion_salida,
                    'confidence': ev.confidence
                }
                for ev in self.vehiculos_emergencia
            ]
        }

        return paquete

    def obtener_resumen_legible(self) -> str:
        """
        Genera un resumen legible del estado actual

        Returns:
            String con resumen formateado
        """
        resumen = f"\n{'='*70}\n"
        resumen += f"ESTADO LOCAL - {self.id}\n"
        resumen += f"{'='*70}\n"
        resumen += f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        resumen += f"CamMask: {'NS' if self.cam_mask == 1 else 'EO'}\n"
        resumen += f"\n"

        for idx, dir in enumerate(self.direcciones):
            visible = (dir in ['N', 'S'] and self.cam_mask == 1) or \
                     (dir in ['E', 'O'] and self.cam_mask == 0)

            resumen += f"Dirección {dir} {'(VISIBLE)' if visible else '(NO VISIBLE)'}:\n"
            resumen += f"  SC (detenidos):    {self.SC[idx]:.1f} veh\n"
            resumen += f"  Vavg (velocidad):  {self.Vavg[idx]:.1f} km/h\n"
            resumen += f"  q (flujo):         {self.q[idx]:.1f} veh/min\n"
            resumen += f"  k (densidad):      {self.k[idx]:.4f} veh/m\n"
            resumen += f"  ICV (congestión):  {self.ICV[idx]:.3f}\n"
            resumen += f"  PI (intensidad):   {self.PI[idx]:.3f}\n"
            resumen += f"  EV (emergencias):  {int(self.EV[idx])}\n"
            resumen += f"\n"

        if self.vehiculos_emergencia:
            resumen += f"Vehículos de Emergencia Activos: {len(self.vehiculos_emergencia)}\n"
            for ev in self.vehiculos_emergencia:
                resumen += f"  - {ev.clase} (ID: {ev.id_tracking}), Dir: {ev.direccion_inicial}\n"

        resumen += f"{'='*70}\n"

        return resumen


# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Crear estado local
    params = ParametrosInterseccion()
    estado = EstadoLocalInterseccion("INT_001", params)

    # Simular detecciones
    vehiculos_norte = [
        {'id': 1, 'velocidad': 3.0, 'clase': 'car', 'confidence': 0.95},
        {'id': 2, 'velocidad': 2.5, 'clase': 'car', 'confidence': 0.92},
        {'id': 3, 'velocidad': 45.0, 'clase': 'car', 'confidence': 0.88},
    ]

    vehiculos_este = [
        {'id': 10, 'velocidad': 15.0, 'clase': 'ambulance', 'confidence': 0.96,
         'pos_x': 25.0, 'pos_y': 5.0, 'vel_x': 5.0, 'vel_y': 0.5},
    ]

    # Configurar cam_mask a NS para ver Norte
    estado.actualizar_cam_mask(1)

    # Actualizar estado
    estado.actualizar_estado(
        vehiculos_por_direccion={
            'N': vehiculos_norte,
            'S': [],
            'E': vehiculos_este,
            'O': []
        },
        cruces_por_direccion={
            'N': 5,
            'S': 3,
            'E': 8,
            'O': 2
        }
    )

    # Mostrar resumen
    print(estado.obtener_resumen_legible())

    # Obtener paquete telemetría
    import json
    paquete = estado.obtener_paquete_telemetria()
    print("\nPaquete de telemetría (JSON):")
    print(json.dumps(paquete, indent=2))
