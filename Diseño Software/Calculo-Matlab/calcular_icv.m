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

    validateattributes(L, {'numeric'}, ...
        {'real', 'finite', 'scalar', 'nonnegative'}, mfilename, 'L', 1);
    validateattributes(V, {'numeric'}, ...
        {'real', 'finite', 'scalar', 'nonnegative'}, mfilename, 'V', 2);
    validateattributes(F, {'numeric'}, ...
        {'real', 'finite', 'scalar', 'nonnegative'}, mfilename, 'F', 3);
    validateattributes(N, {'numeric'}, ...
        {'real', 'finite', 'scalar', 'nonnegative'}, mfilename, 'N', 4);

    campos = {'L_max', 'V_max', 'F_sat', 'L_carril', 'rho_jam', 'pesos'};
    if ~isstruct(parametros) || ~all(isfield(parametros, campos))
        error('parametros debe contener L_max, V_max, F_sat, L_carril, rho_jam y pesos.');
    end
    validateattributes(parametros.L_max, {'numeric'}, {'real', 'finite', 'scalar', 'positive'});
    validateattributes(parametros.V_max, {'numeric'}, {'real', 'finite', 'scalar', 'positive'});
    validateattributes(parametros.F_sat, {'numeric'}, {'real', 'finite', 'scalar', 'positive'});
    validateattributes(parametros.L_carril, {'numeric'}, {'real', 'finite', 'scalar', 'positive'});
    validateattributes(parametros.rho_jam, {'numeric'}, {'real', 'finite', 'scalar', 'positive'});
    validateattributes(parametros.pesos, {'numeric'}, ...
        {'real', 'finite', 'vector', 'numel', 4, 'nonnegative'});

    if abs(sum(parametros.pesos) - 1) > 1e-6
        error('La suma de los pesos debe ser igual a 1.');
    end

    % Mantener el mismo caso sin tráfico que el núcleo Python canónico.
    if N == 0
        ICV = 0;
        clasificacion = 'Bajo';
        color = 'Verde';
        return;
    end

    %% Cálculo de densidad normalizada
    rho = N / parametros.L_carril;
    D_norm = min(max(rho / parametros.rho_jam, 0), 1);

    %% Cálculo del ICV
    w = parametros.pesos(:);
    L_norm = min(max(L / parametros.L_max, 0), 1);
    V_norm = min(max(1 - V / parametros.V_max, 0), 1);
    F_norm = min(max(F / parametros.F_sat, 0), 1);
    ICV = w(1) * L_norm + ...
          w(2) * V_norm + ...
          w(3) * F_norm + ...
          w(4) * D_norm;
    ICV = min(max(ICV, 0), 1);

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
