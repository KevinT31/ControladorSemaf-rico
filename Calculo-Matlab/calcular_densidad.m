function [rho, D_norm] = calcular_densidad(N, L_carril, rho_jam)
% calcular_densidad - Calcula la densidad vehicular y su versión normalizada
%
% Entradas:
%   N         - Número de vehículos en el carril
%   L_carril  - Longitud del carril (m)
%   rho_jam   - Densidad de atasco típica (veh/m), por defecto 0.2
%
% Salidas:
%   rho       - Densidad vehicular (veh/m)
%   D_norm    - Densidad normalizada ∈ [0,1]

    %% Validación de entradas
    if nargin < 3
        rho_jam = 0.2; % Valor típico si no se especifica
    end

    if L_carril <= 0
        error('La longitud del carril debe ser mayor que cero.');
    end

    %% Cálculo de densidad
    rho = N / L_carril;

    %% Normalización
    D_norm = min(rho / rho_jam, 1);

    %% Mostrar resultados (opcional)
    fprintf('Densidad = %.3f veh/m, Densidad Normalizada = %.3f\n', rho, D_norm);
end