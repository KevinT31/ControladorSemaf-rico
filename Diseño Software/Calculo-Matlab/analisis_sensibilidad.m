% analisis_sensibilidad.m - Análisis de sensibilidad del ICV ante variaciones del 10%

clear; clc;

%% Parámetros base del sistema
parametros.L_max = 150;
parametros.V_max = 60;
parametros.F_sat = 30;
parametros.L_carril = 300;
parametros.rho_jam = 0.2;
parametros.pesos = [0.35, 0.25, 0.25, 0.15];

%% Valores base del caso de referencia
L_base = 75;     % Longitud de cola (m)
V_base = 25;     % Velocidad promedio (km/h)
F_base = 22;     % Flujo vehicular (veh/min)
N_base = 40;     % Número de vehículos

%% Cálculo del ICV base
[ICV_base, ~, ~] = calcular_icv(L_base, V_base, F_base, N_base, parametros);

%% Variaciones del 10% en cada variable
delta = 0.10;

% Longitud de cola
L_var = L_base * (1 + delta);
[ICV_L, ~, ~] = calcular_icv(L_var, V_base, F_base, N_base, parametros);
delta_ICV_L = ICV_L - ICV_base;

% Velocidad
V_var = V_base * (1 + delta);
[ICV_V, ~, ~] = calcular_icv(L_base, V_var, F_base, N_base, parametros);
delta_ICV_V = ICV_V - ICV_base;

% Flujo
F_var = F_base * (1 + delta);
[ICV_F, ~, ~] = calcular_icv(L_base, V_base, F_var, N_base, parametros);
delta_ICV_F = ICV_F - ICV_base;

% Densidad (N)
N_var = N_base * (1 + delta);
[ICV_D, ~, ~] = calcular_icv(L_base, V_base, F_base, N_var, parametros);
delta_ICV_D = ICV_D - ICV_base;

%% Mostrar resultados
fprintf('=== Análisis de Sensibilidad del ICV ===\n');
fprintf('ICV base: %.3f\n\n', ICV_base);
fprintf('ΔICV por +10%% en L: %.3f\n', delta_ICV_L);
fprintf('ΔICV por +10%% en V: %.3f\n', delta_ICV_V);
fprintf('ΔICV por +10%% en F: %.3f\n', delta_ICV_F);
fprintf('ΔICV por +10%% en D: %.3f\n', delta_ICV_D);

%% Visualización
variaciones = [delta_ICV_L, delta_ICV_V, delta_ICV_F, delta_ICV_D];
labels = {'Longitud de Cola (L)', 'Velocidad (V)', 'Flujo (F)', 'Densidad (D)'};

figure('Name','Sensibilidad del ICV','NumberTitle','off');
bar(variaciones, 'FaceColor',[0.2 0.6 0.8]);
title('Variación del ICV ante +10% en cada variable');
ylabel('ΔICV');
xticklabels(labels);
grid on;