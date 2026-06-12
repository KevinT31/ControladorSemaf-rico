function [ICV, clasificacion, color] = calcular_icv(L, V, F, N, parametros)
% calcular_icv - Calcula el Índice de Congestión Vehicular (ICV)
%
% Entradas:
%   L          - Longitud de cola observada (m)
%   V          - Velocidad promedio medida (km/h)
%   F          - Flujo vehicular observado (veh/min)
%   N          - Número de vehículos en el carril
%   parametros - Estructura con campos:
%       .L_max      - Longitud máxima de almacenamiento (m)
%       .V_max      - Velocidad libre de flujo (km/h)
%       .F_sat      - Flujo de saturación teórico (veh/min)
%       .L_carril   - Longitud del carril (m)
%       .rho_jam    - Densidad de atasco típica (veh/m)
%       .pesos      - Vector [w1, w2, w3, w4], suma = 1
%
% Salidas:
%   ICV           - Índice de congestión normalizado [0,1]
%   clasificacion - 'Bajo', 'Medio' o 'Alto'
%   color         - 'Verde', 'Amarillo' o 'Rojo'

    %% Validación de entradas
    if nargin < 5
        error('Faltan argumentos. Debes proporcionar L, V, F, N y parametros.');
    end

    if abs(sum(parametros.pesos) - 1) > 1e-3
        error('La suma de los pesos debe ser igual a 1.');
    end

    %% Cálculo de densidad normalizada
    rho = N / parametros.L_carril;
    D_norm = min(rho / parametros.rho_jam, 1);

    %% Cálculo del ICV
    w = parametros.pesos;
    ICV = w(1) * (L / parametros.L_max) + ...
          w(2) * (1 - V / parametros.V_max) + ...
          w(3) * (F / parametros.F_sat) + ...
          w(4) * D_norm;

    %% Clasificación semafórica
    if ICV < 0.3
        clasificacion = 'Bajo';
        color = 'Verde';
    elseif ICV < 0.6
        clasificacion = 'Medio';
        color = 'Amarillo';
    else
        clasificacion = 'Alto';
        color = 'Rojo';
    end

    %% Mostrar resultados (opcional)
    fprintf('ICV = %.3f → %s (%s)\n', ICV, clasificacion, color);
end