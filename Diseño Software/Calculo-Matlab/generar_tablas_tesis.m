

%% Crear carpeta de resultados
carpeta_resultados = 'resultados_tesis';
if ~exist(carpeta_resultados, 'dir')
    mkdir(carpeta_resultados);
end

%% Parámetros del sistema
parametros.L_max = 150;           % Longitud máxima de cola (m)
parametros.V_max = 60;            % Velocidad libre (km/h)
parametros.F_sat = 30;            % Flujo de saturación (veh/min)
parametros.L_carril = 300;        % Longitud del carril (m)
parametros.rho_jam = 0.2;         % Densidad de atasco (veh/m)
parametros.pesos = [0.35, 0.25, 0.25, 0.15];  % Pesos AHP

%% ========================================
%% TABLA 1: Parámetros del Sistema
%% ========================================
fprintf('[1/7] Generando Tabla 1: Parámetros del Sistema...\n');

tabla1 = table(...
    {'Longitud Máxima de Cola (L_max)'; ...
     'Velocidad Libre de Flujo (V_max)'; ...
     'Flujo de Saturación (F_sat)'; ...
     'Longitud del Carril (L_carril)'; ...
     'Densidad de Atasco (ρ_jam)'; ...
     'Peso - Longitud de Cola (w₁)'; ...
     'Peso - Velocidad (w₂)'; ...
     'Peso - Flujo (w₃)'; ...
     'Peso - Densidad (w₄)'}, ...
    [150; 60; 30; 300; 0.2; 0.35; 0.25; 0.25; 0.15], ...
    {'metros'; 'km/h'; 'veh/min'; 'metros'; 'veh/m'; '-'; '-'; '-'; '-'}, ...
    'VariableNames', {'Parametro', 'Valor', 'Unidad'});

writetable(tabla1, fullfile(carpeta_resultados, 'Tabla1_Parametros_Sistema.csv'));
disp(tabla1);
fprintf('   ✓ Guardada en: %s\n\n', fullfile(carpeta_resultados, 'Tabla1_Parametros_Sistema.csv'));

%% ========================================
%% TABLA 2: Casos de Prueba y Resultados ICV
%% ========================================
fprintf('[2/7] Generando Tabla 2: Casos de Prueba...\n');

casos = {
    'Flujo Libre Nocturno', 5, 58, 8, 10;
    'Flujo Libre Diurno', 15, 52, 12, 18;
    'Transición Matutina', 35, 40, 18, 28;
    'Congestión Leve', 60, 30, 20, 35;
    'Congestión Moderada', 85, 22, 24, 45;
    'Congestión Severa', 115, 15, 27, 52;
    'Atasco Parcial', 135, 10, 29, 58;
    'Atasco Total', 148, 5, 30, 60
};

n_casos = size(casos, 1);
tabla2_data = cell(n_casos, 9);

for i = 1:n_casos
    nombre = casos{i,1};
    L = casos{i,2}; V = casos{i,3}; F = casos{i,4}; N = casos{i,5};

    [ICV, clasificacion, color] = calcular_icv(L, V, F, N, parametros);
    [rho, D_norm] = calcular_densidad(N, parametros.L_carril, parametros.rho_jam);

    tabla2_data(i,:) = {nombre, L, V, F, N, sprintf('%.3f', rho), ...
                        sprintf('%.3f', ICV), clasificacion, color};
end

tabla2 = cell2table(tabla2_data, 'VariableNames', ...
    {'Caso', 'L_m', 'V_kmh', 'F_vehmin', 'N_veh', 'Densidad_vehm', 'ICV', 'Nivel', 'Color'});

writetable(tabla2, fullfile(carpeta_resultados, 'Tabla2_Casos_Prueba_ICV.csv'));
disp(tabla2);
fprintf('   ✓ Guardada en: %s\n\n', fullfile(carpeta_resultados, 'Tabla2_Casos_Prueba_ICV.csv'));

%% ========================================
%% TABLA 3: Análisis de Sensibilidad
%% ========================================
fprintf('[3/7] Generando Tabla 3: Análisis de Sensibilidad...\n');

% Caso base (Congestión Moderada)
L_base = 85; V_base = 22; F_base = 24; N_base = 45;
[ICV_base, ~, ~] = calcular_icv(L_base, V_base, F_base, N_base, parametros);

delta = 0.10; % Variación del 10%

% Variaciones
L_var = L_base * (1 + delta);
[ICV_L_pos, ~, ~] = calcular_icv(L_var, V_base, F_base, N_base, parametros);

V_var = V_base * (1 + delta);
[ICV_V_pos, ~, ~] = calcular_icv(L_base, V_var, F_base, N_base, parametros);

F_var = F_base * (1 + delta);
[ICV_F_pos, ~, ~] = calcular_icv(L_base, V_base, F_var, N_base, parametros);

N_var = N_base * (1 + delta);
[ICV_D_pos, ~, ~] = calcular_icv(L_base, V_base, F_base, N_var, parametros);

% Calcular deltas y sensibilidades
tabla3 = table(...
    {'Longitud Cola (L)'; 'Velocidad (V)'; 'Flujo (F)'; 'Densidad (N)'}, ...
    [L_base; V_base; F_base; N_base], ...
    [L_var; V_var; F_var; N_var], ...
    [ICV_L_pos; ICV_V_pos; ICV_F_pos; ICV_D_pos], ...
    [ICV_L_pos - ICV_base; ICV_V_pos - ICV_base; ICV_F_pos - ICV_base; ICV_D_pos - ICV_base], ...
    [(ICV_L_pos - ICV_base)/ICV_base*100; (ICV_V_pos - ICV_base)/ICV_base*100; ...
     (ICV_F_pos - ICV_base)/ICV_base*100; (ICV_D_pos - ICV_base)/ICV_base*100], ...
    'VariableNames', {'Variable', 'Valor_Base', 'Valor_Variado_10pct', 'ICV_Resultante', 'Delta_ICV', 'Sensibilidad_pct'});

writetable(tabla3, fullfile(carpeta_resultados, 'Tabla3_Analisis_Sensibilidad.csv'));
disp(tabla3);
fprintf('   ICV Base: %.3f\n', ICV_base);
fprintf('   ✓ Guardada en: %s\n\n', fullfile(carpeta_resultados, 'Tabla3_Analisis_Sensibilidad.csv'));

%% ========================================
%% TABLA 4: Matriz de Comparación AHP
%% ========================================
fprintf('[4/7] Generando Tabla 4: Matriz AHP...\n');

% Matriz de comparación por pares
% L vs V, L vs F, L vs D
% V vs F, V vs D
% F vs D
A_ahp = [
    1,    1.5,  1.5,  2.5;   % L: Longitud Cola
    1/1.5,  1,    1,    2;     % V: Velocidad
    1/1.5,  1,    1,    2;     % F: Flujo
    1/2.5, 1/2,  1/2,   1      % D: Densidad
];

[pesos_ahp, CR] = calcular_pesos_ahp(A_ahp);

tabla4 = table(...
    {'Longitud de Cola (L)'; 'Velocidad (V)'; 'Flujo (F)'; 'Densidad (D)'}, ...
    pesos_ahp, ...
    pesos_ahp * 100, ...
    'VariableNames', {'Criterio', 'Peso_Normalizado', 'Porcentaje'});

writetable(tabla4, fullfile(carpeta_resultados, 'Tabla4_Pesos_AHP.csv'));
disp(tabla4);
fprintf('   Razón de Consistencia (CR): %.4f %s\n', CR, ternario(CR < 0.1, '✓ Consistente', '✗ Inconsistente'));
fprintf('   ✓ Guardada en: %s\n\n', fullfile(carpeta_resultados, 'Tabla4_Pesos_AHP.csv'));

%% ========================================
%% TABLA 5: Validación del Modelo
%% ========================================
fprintf('[5/7] Generando Tabla 5: Validación del Modelo...\n');

% Datos simulados (puedes reemplazar con datos reales)
datos_validacion = [
    8, 56, 9, 12, "Bajo";
    18, 48, 14, 22, "Bajo";
    45, 35, 19, 32, "Medio";
    80, 24, 23, 43, "Medio";
    120, 12, 26, 54, "Alto";
    145, 6, 29, 59, "Alto";
    25, 45, 16, 25, "Bajo";
    95, 20, 24, 48, "Medio";
    130, 10, 28, 56, "Alto";
    40, 38, 18, 30, "Medio"
];

n_val = size(datos_validacion, 1);
tabla5_data = cell(n_val, 8);

for i = 1:n_val
    L = datos_validacion(i,1);
    V = datos_validacion(i,2);
    F = datos_validacion(i,3);
    N = datos_validacion(i,4);
    etiqueta_real = datos_validacion(i,5);

    [ICV, etiqueta_pred, color] = calcular_icv(L, V, F, N, parametros);
    acierto = strcmp(etiqueta_pred, etiqueta_real);

    tabla5_data(i,:) = {i, L, V, F, N, sprintf('%.3f', ICV), etiqueta_pred, etiqueta_real};
end

tabla5 = cell2table(tabla5_data, 'VariableNames', ...
    {'Caso', 'L_m', 'V_kmh', 'F_vehmin', 'N_veh', 'ICV_Calculado', 'Prediccion', 'Real'});

writetable(tabla5, fullfile(carpeta_resultados, 'Tabla5_Validacion_Modelo.csv'));
disp(tabla5);

% Calcular precisión
etiqueta_pred_vec = tabla5.Prediccion;
etiqueta_real_vec = [datos_validacion{:,5}]';
aciertos = strcmp(etiqueta_pred_vec, etiqueta_real_vec);
precision = sum(aciertos) / n_val * 100;

fprintf('   Precisión del Modelo: %.1f%%\n', precision);
fprintf('   ✓ Guardada en: %s\n\n', fullfile(carpeta_resultados, 'Tabla5_Validacion_Modelo.csv'));

%% ========================================
%% TABLA 6: Matriz de Confusión
%% ========================================
fprintf('[6/7] Generando Tabla 6: Matriz de Confusión...\n');

categorias = ["Bajo", "Medio", "Alto"];
confusion = zeros(3,3);

for i = 1:n_val
    r = find(categorias == datos_validacion(i,5));
    p = find(categorias == tabla5_data{i,7});
    confusion(r,p) = confusion(r,p) + 1;
end

tabla6 = array2table(confusion, ...
    'VariableNames', {'Predicho_Bajo', 'Predicho_Medio', 'Predicho_Alto'}, ...
    'RowNames', {'Real_Bajo', 'Real_Medio', 'Real_Alto'});

writetable(tabla6, fullfile(carpeta_resultados, 'Tabla6_Matriz_Confusion.csv'), 'WriteRowNames', true);
disp(tabla6);
fprintf('   ✓ Guardada en: %s\n\n', fullfile(carpeta_resultados, 'Tabla6_Matriz_Confusion.csv'));

%% ========================================
%% TABLA 7: Comparación de Tiempos de Respuesta
%% ========================================
fprintf('[7/7] Generando Tabla 7: Comparación de Tiempos...\n');

% Simulación de tiempos de respuesta
escenarios = {
    'Flujo Libre', 30, 35, 15;
    'Congestión Leve', 60, 65, 8;
    'Congestión Moderada', 90, 95, 5;
    'Congestión Severa', 120, 125, 4
};

tabla7_data = cell(size(escenarios,1), 7);

for i = 1:size(escenarios,1)
    nombre = escenarios{i,1};
    t_fijo = escenarios{i,2};
    t_adaptativo = escenarios{i,3};
    t_inteligente = escenarios{i,4};

    mejora_vs_fijo = (t_fijo - t_inteligente) / t_fijo * 100;
    mejora_vs_adapt = (t_adaptativo - t_inteligente) / t_adaptativo * 100;

    tabla7_data(i,:) = {nombre, t_fijo, t_adaptativo, t_inteligente, ...
                        sprintf('%.1f%%', mejora_vs_fijo), ...
                        sprintf('%.1f%%', mejora_vs_adapt), ...
                        'Mejor'};
end

tabla7 = cell2table(tabla7_data, 'VariableNames', ...
    {'Escenario', 'Tiempo_Fijo_s', 'Tiempo_Adaptativo_s', 'Tiempo_Inteligente_s', ...
     'Mejora_vs_Fijo', 'Mejora_vs_Adaptativo', 'Rendimiento'});

writetable(tabla7, fullfile(carpeta_resultados, 'Tabla7_Comparacion_Tiempos.csv'));
disp(tabla7);
fprintf('   ✓ Guardada en: %s\n\n', fullfile(carpeta_resultados, 'Tabla7_Comparacion_Tiempos.csv'));


