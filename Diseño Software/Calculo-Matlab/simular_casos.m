% simular_casos.m - Simula y visualiza casos de prueba del ICV

clear; clc;

%% Parámetros del sistema
parametros.L_max = 150;           % Longitud máxima de cola (m)
parametros.V_max = 60;            % Velocidad libre (km/h)
parametros.F_sat = 30;            % Flujo de saturación (veh/min)
parametros.L_carril = 300;        % Longitud del carril (m)
parametros.rho_jam = 0.2;         % Densidad de atasco (veh/m)
parametros.pesos = [0.35, 0.25, 0.25, 0.15];  % Pesos AHP

%% Casos de prueba
casos = {
    struct('nombre','Flujo Libre', 'L',10, 'V',55, 'F',10, 'N',15),
    struct('nombre','Congestión Moderada', 'L',75, 'V',25, 'F',22, 'N',40),
    struct('nombre','Atasco Severo', 'L',140, 'V',8, 'F',28, 'N',60)
};

%% Inicializar resultados
ICVs = zeros(1, length(casos));
colores = strings(1, length(casos));
etiquetas = strings(1, length(casos));

%% Simulación
fprintf('=== Simulación de Casos de Prueba ===\n\n');
for i = 1:length(casos)
    caso = casos{i};
    [ICV, clasificacion, color] = calcular_icv(caso.L, caso.V, caso.F, caso.N, parametros);
    ICVs(i) = ICV;
    colores(i) = color;
    etiquetas(i) = caso.nombre;
    fprintf('%s → ICV = %.3f → %s (%s)\n', caso.nombre, ICV, clasificacion, color);
end

%% Visualización
figure('Name','Clasificación de Congestión','NumberTitle','off');
bar(ICVs, 'FaceColor','flat');
title('Índice de Congestión Vehicular (ICV)');
ylabel('ICV [0–1]');
xticklabels(etiquetas);
ylim([0 1]);

% Colores semafóricos
for i = 1:length(casos)
    switch colores(i)
        case 'Verde'
            colorRGB = [0.2 0.8 0.2];
        case 'Amarillo'
            colorRGB = [1.0 0.8 0.1];
        case 'Rojo'
            colorRGB = [0.9 0.2 0.2];
    end
    set(gca.Children(i), 'CData', colorRGB);
end

grid on;