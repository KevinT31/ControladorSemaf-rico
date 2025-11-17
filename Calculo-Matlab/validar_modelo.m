% validar_modelo.m - Valida el modelo del ICV comparando con etiquetas reales

clear; clc;

%% Parámetros del sistema
parametros.L_max = 150;
parametros.V_max = 60;
parametros.F_sat = 30;
parametros.L_carril = 300;
parametros.rho_jam = 0.2;
parametros.pesos = [0.35, 0.25, 0.25, 0.15];

%% Datos simulados (puedes reemplazar con CSV real)
% Cada fila: [L, V, F, N, etiqueta_real]
datos = [
    10, 55, 10, 15, "Bajo";
    75, 25, 22, 40, "Medio";
    140, 8, 28, 60, "Alto";
    50, 40, 18, 30, "Medio";
    130, 10, 25, 55, "Alto";
    20, 50, 12, 20, "Bajo"
];

n = size(datos, 1);
ICV_pred = zeros(n, 1);
etiqueta_pred = strings(n, 1);
etiqueta_real = datos(:, 5);

%% Clasificación automática
for i = 1:n
    L = datos(i,1); V = datos(i,2); F = datos(i,3); N = datos(i,4);
    [ICV, clase, ~] = calcular_icv(L, V, F, N, parametros);
    ICV_pred(i) = ICV;
    etiqueta_pred(i) = clase;
end

%% Métricas de validación
aciertos = etiqueta_pred == etiqueta_real;
precision = sum(aciertos) / n;

fprintf('=== Validación del Modelo ICV ===\n');
fprintf('Precisión de clasificación: %.2f%%\n\n', precision * 100);

%% Matriz de confusión
categorias = ["Bajo", "Medio", "Alto"];
confusion = zeros(3,3);
for i = 1:n
    r = find(categorias == etiqueta_real(i));
    p = find(categorias == etiqueta_pred(i));
    confusion(r,p) = confusion(r,p) + 1;
end

disp('Matriz de Confusión (Real vs. Predicho):');
disp(array2table(confusion, 'VariableNames',categorias, 'RowNames',categorias));

%% Correlación con etiquetas ordinales
ordinal = containers.Map({"Bajo","Medio","Alto"}, [1,2,3]);
y_real = cell2mat(values(ordinal, cellstr(etiqueta_real)));
y_pred = cell2mat(values(ordinal, cellstr(etiqueta_pred)));
R = corr(ICV_pred, y_real, 'type','Spearman');

fprintf('Correlación ICV vs. Etiqueta Real (Spearman): %.3f\n', R);

%% Visualización
figure('Name','ICV vs. Etiqueta Real','NumberTitle','off');
scatter(ICV_pred, y_real, 80, 'filled');
xlabel('ICV calculado');
ylabel('Etiqueta real (ordinal)');
yticks([1 2 3]); yticklabels(categorias);
title('Validación del Modelo ICV');
grid on;