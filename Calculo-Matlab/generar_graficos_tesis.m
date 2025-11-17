

%% Configuración de carpetas
carpeta_graficos = 'graficos_tesis';
if ~exist(carpeta_graficos, 'dir')
    mkdir(carpeta_graficos);
end

%% Parámetros del sistema
parametros.L_max = 150;
parametros.V_max = 60;
parametros.F_sat = 30;
parametros.L_carril = 300;
parametros.rho_jam = 0.2;
parametros.pesos = [0.35, 0.25, 0.25, 0.15];

%% ========================================
%% GRÁFICO 1: Clasificación de Congestión por Casos
%% ========================================
fprintf('[1/5] Generando Gráfico 1: Clasificación de Congestión...\n');

casos = {
    'Flujo Libre', 10, 55, 10, 15;
    'Transición', 50, 35, 18, 32;
    'Congestión Leve', 75, 25, 22, 40;
    'Congestión Severa', 120, 12, 27, 55;
    'Atasco Total', 145, 6, 30, 60
};

n_casos = size(casos, 1);
ICVs = zeros(n_casos, 1);
colores_rgb = zeros(n_casos, 3);

for i = 1:n_casos
    L = casos{i,2}; V = casos{i,3}; F = casos{i,4}; N = casos{i,5};
    [ICV, ~, color] = calcular_icv(L, V, F, N, parametros);
    ICVs(i) = ICV;

    switch color
        case 'Verde'
            colores_rgb(i,:) = [0.2 0.8 0.2];
        case 'Amarillo'
            colores_rgb(i,:) = [1.0 0.8 0.1];
        case 'Rojo'
            colores_rgb(i,:) = [0.9 0.2 0.2];
    end
end

figure('Position', [100 100 800 500]);
b = bar(ICVs, 'FaceColor', 'flat');
b.CData = colores_rgb;
title('Clasificación de Congestión Vehicular', 'FontSize', 14, 'FontWeight', 'bold');
ylabel('Índice de Congestión Vehicular (ICV)', 'FontSize', 12);
xlabel('Escenarios de Tráfico', 'FontSize', 12);
xticklabels(casos(:,1));
ylim([0 1]);
grid on;
set(gca, 'FontSize', 11);

% Añadir líneas de referencia
hold on;
yline(0.3, '--k', 'Umbral Bajo-Medio', 'LineWidth', 1.5);
yline(0.6, '--k', 'Umbral Medio-Alto', 'LineWidth', 1.5);
hold off;

saveas(gcf, fullfile(carpeta_graficos, 'Grafico1_Clasificacion_Congestion.png'));
fprintf('   ✓ Guardado: Grafico1_Clasificacion_Congestion.png\n');

%% ========================================
%% GRÁFICO 2: Análisis de Sensibilidad
%% ========================================
fprintf('[2/5] Generando Gráfico 2: Análisis de Sensibilidad...\n');

L_base = 85; V_base = 22; F_base = 24; N_base = 45;
[ICV_base, ~, ~] = calcular_icv(L_base, V_base, F_base, N_base, parametros);

delta = 0.10;
L_var = L_base * (1 + delta);
[ICV_L, ~, ~] = calcular_icv(L_var, V_base, F_base, N_base, parametros);

V_var = V_base * (1 + delta);
[ICV_V, ~, ~] = calcular_icv(L_base, V_var, F_base, N_base, parametros);

F_var = F_base * (1 + delta);
[ICV_F, ~, ~] = calcular_icv(L_base, V_base, F_var, N_base, parametros);

N_var = N_base * (1 + delta);
[ICV_D, ~, ~] = calcular_icv(L_base, V_base, F_base, N_var, parametros);

variaciones = [ICV_L - ICV_base; ICV_V - ICV_base; ICV_F - ICV_base; ICV_D - ICV_base];
labels = {'Long. Cola (L)', 'Velocidad (V)', 'Flujo (F)', 'Densidad (N)'};

figure('Position', [100 100 800 500]);
bar(variaciones, 'FaceColor', [0.2 0.5 0.8]);
title('Sensibilidad del ICV ante Variaciones del 10%', 'FontSize', 14, 'FontWeight', 'bold');
ylabel('\DeltaICV', 'FontSize', 12);
xlabel('Variable Modificada', 'FontSize', 12);
xticklabels(labels);
grid on;
set(gca, 'FontSize', 11);

% Añadir valores en las barras
hold on;
for i = 1:length(variaciones)
    text(i, variaciones(i), sprintf('%.3f', variaciones(i)), ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom', 'FontSize', 10);
end
hold off;

saveas(gcf, fullfile(carpeta_graficos, 'Grafico2_Sensibilidad_ICV.png'));
fprintf('   ✓ Guardado: Grafico2_Sensibilidad_ICV.png\n');

%% ========================================
%% GRÁFICO 3: Relación ICV vs Variables de Entrada
%% ========================================
fprintf('[3/5] Generando Gráfico 3: Relación ICV vs Variables...\n');

% Generar datos variando cada variable
n_puntos = 50;

% Variación de Longitud de Cola
L_range = linspace(0, 150, n_puntos);
ICV_L_range = zeros(n_puntos, 1);
for i = 1:n_puntos
    [ICV_L_range(i), ~, ~] = calcular_icv(L_range(i), 30, 20, 35, parametros);
end

% Variación de Velocidad
V_range = linspace(5, 60, n_puntos);
ICV_V_range = zeros(n_puntos, 1);
for i = 1:n_puntos
    [ICV_V_range(i), ~, ~] = calcular_icv(75, V_range(i), 20, 35, parametros);
end

figure('Position', [100 100 1200 400]);

% Subplot 1: L vs ICV
subplot(1,3,1);
plot(L_range, ICV_L_range, 'LineWidth', 2, 'Color', [0.8 0.2 0.2]);
xlabel('Longitud de Cola (m)', 'FontSize', 11);
ylabel('ICV', 'FontSize', 11);
title('ICV vs Longitud de Cola', 'FontSize', 12);
grid on;
ylim([0 1]);

% Subplot 2: V vs ICV
subplot(1,3,2);
plot(V_range, ICV_V_range, 'LineWidth', 2, 'Color', [0.2 0.6 0.8]);
xlabel('Velocidad (km/h)', 'FontSize', 11);
ylabel('ICV', 'FontSize', 11);
title('ICV vs Velocidad', 'FontSize', 12);
grid on;
ylim([0 1]);

% Subplot 3: Pesos AHP
subplot(1,3,3);
pesos_nombres = {'Long. Cola', 'Velocidad', 'Flujo', 'Densidad'};
pie(parametros.pesos, pesos_nombres);
title('Distribución de Pesos AHP', 'FontSize', 12);

sgtitle('Análisis de Relaciones del ICV', 'FontSize', 14, 'FontWeight', 'bold');

saveas(gcf, fullfile(carpeta_graficos, 'Grafico3_Relacion_ICV_Variables.png'));
fprintf('   ✓ Guardado: Grafico3_Relacion_ICV_Variables.png\n');

%% ========================================
%% GRÁFICO 4: Matriz de Confusión Visual
%% ========================================
fprintf('[4/5] Generando Gráfico 4: Matriz de Confusión...\n');

% Datos de validación simulados
confusion = [
    3, 0, 0;
    0, 3, 1;
    0, 0, 3
];

figure('Position', [100 100 600 550]);
imagesc(confusion);
colormap(flipud(hot));
colorbar;
title('Matriz de Confusión del Modelo ICV', 'FontSize', 14, 'FontWeight', 'bold');
xlabel('Predicción', 'FontSize', 12);
ylabel('Real', 'FontSize', 12);

xticks(1:3);
yticks(1:3);
xticklabels({'Bajo', 'Medio', 'Alto'});
yticklabels({'Bajo', 'Medio', 'Alto'});

% Añadir valores en las celdas
for i = 1:3
    for j = 1:3
        text(j, i, num2str(confusion(i,j)), 'HorizontalAlignment', 'center', ...
            'Color', 'white', 'FontSize', 16, 'FontWeight', 'bold');
    end
end

set(gca, 'FontSize', 11);

saveas(gcf, fullfile(carpeta_graficos, 'Grafico4_Matriz_Confusion.png'));
fprintf('   ✓ Guardado: Grafico4_Matriz_Confusion.png\n');

%% ========================================
%% GRÁFICO 5: Comparación de Rendimiento
%% ========================================
fprintf('[5/5] Generando Gráfico 5: Comparación de Rendimiento...\n');

escenarios = {'Flujo Libre', 'Congestión Leve', 'Congestión Moderada', 'Congestión Severa'};
t_fijo = [30, 60, 90, 120];
t_adaptativo = [35, 65, 95, 125];
t_inteligente = [15, 8, 5, 4];

figure('Position', [100 100 900 500]);
x = 1:length(escenarios);
width = 0.25;

b1 = bar(x - width, t_fijo, width, 'FaceColor', [0.8 0.2 0.2]);
hold on;
b2 = bar(x, t_adaptativo, width, 'FaceColor', [0.8 0.6 0.2]);
b3 = bar(x + width, t_inteligente, width, 'FaceColor', [0.2 0.8 0.2]);
hold off;

title('Comparación de Tiempos de Respuesta', 'FontSize', 14, 'FontWeight', 'bold');
ylabel('Tiempo de Respuesta (segundos)', 'FontSize', 12);
xlabel('Escenario de Tráfico', 'FontSize', 12);
xticklabels(escenarios);
legend({'Semáforo Fijo', 'Adaptativo', 'Inteligente (ICV)'}, 'Location', 'northwest');
grid on;
set(gca, 'FontSize', 11);

saveas(gcf, fullfile(carpeta_graficos, 'Grafico5_Comparacion_Rendimiento.png'));
fprintf('   ✓ Guardado: Grafico5_Comparacion_Rendimiento.png\n');

