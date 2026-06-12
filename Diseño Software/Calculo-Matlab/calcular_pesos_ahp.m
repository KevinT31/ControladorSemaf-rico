function [pesos, CR] = calcular_pesos_ahp(A)
% calcular_pesos_ahp - Calcula los pesos normalizados y el índice de consistencia (CR)
% a partir de una matriz de comparación por pares A (AHP)
%
% Entradas:
%   A     - Matriz cuadrada de comparación por pares (n x n)
%
% Salidas:
%   pesos - Vector de pesos normalizados (suma = 1)
%   CR    - Índice de consistencia (CR < 0.1 es aceptable)

    %% Validación
    [n, m] = size(A);
    if n ~= m
        error('La matriz A debe ser cuadrada.');
    end

    %% Paso 1: Normalizar columnas
    col_sum = sum(A, 1);
    A_norm = A ./ col_sum;

    %% Paso 2: Calcular pesos promedio por fila
    pesos = mean(A_norm, 2);
    pesos = pesos / sum(pesos);  % Normalizar por si acaso

    %% Paso 3: Calcular λ_max
    Aw = A * pesos;
    lambda_max = mean(Aw ./ pesos);

    %% Paso 4: Calcular índice de consistencia (CI) y razón de consistencia (CR)
    CI = (lambda_max - n) / (n - 1);
    RI = obtener_RI(n);
    CR = CI / RI;

    %% Mostrar resultados
    fprintf('=== Cálculo de Pesos AHP ===\n');
    disp(table((1:n)', pesos, 'VariableNames', {'Variable','Peso'}));
    fprintf('λ_max = %.4f\n', lambda_max);
    fprintf('CI = %.4f\n', CI);
    fprintf('CR = %.4f → %s\n', CR, ternario(CR < 0.1, 'Consistente ✓', 'Inconsistente ✗'));
end

function RI = obtener_RI(n)
% obtener_RI - Devuelve el valor del Índice Aleatorio (RI) para tamaño n
    RI_table = [ ...
        0.00, 0.00, 0.58, 0.90, 1.12, ...
        1.24, 1.32, 1.41, 1.45, 1.49, ...
        1.51, 1.48, 1.56, 1.57, 1.59];
    if n <= length(RI_table)
        RI = RI_table(n);
    else
        RI = 1.59; % Aproximación para n > 15
    end
end

function resultado = ternario(condicion, valor_verdadero, valor_falso)
% ternario - Operador ternario simple
    if condicion
        resultado = valor_verdadero;
    else
        resultado = valor_falso;
    end
end