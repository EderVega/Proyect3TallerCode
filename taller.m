clear
pkg load signal

% Frecuencias de muestreo y corte
sf = 40e3;       % Frecuencia de muestreo (40 kHz)
sf2 = sf/2;      % Frecuencia de Nyquist (20 kHz)

% Frecuencias de corte originales
fc1 = 20;        % Frecuencia pasa bajas original (20 Hz)
fc2 = 2e3;       % Frecuencia pasa altas original (2 kHz)
fc3 = 4e3;       % Nueva frecuencia pasa bajas (4 kHz)

% Generación de señal de prueba (impulso + dos tonos)
data = [[1; zeros(sf-1, 1)], sinetone(fc1, sf, 1, 1) + sinetone(fc2, sf, 1, 1)];

% Diseño de filtros originales
[b1, a1] = butter(1, fc1/sf2);         % Pasa bajas 20 Hz (1er orden)
[b2, a2] = butter(1, fc2/sf2, "high"); % Pasa altas 2 kHz (1er orden)

% Nuevo filtro pasa bajas de 4 kHz (2do orden para mejor rendimiento)
[b3, a3] = butter(2, fc3/sf2);         % Pasa bajas 4 kHz (2do orden)

% Aplicar todos los filtros
filtered1 = filter(b1, a1, data);      % Filtro pasa bajas 20 Hz
filtered2 = filter(b2, a2, data);      % Filtro pasa altas 2 kHz
filtered3 = filter(b3, a3, data);      % Nuevo filtro pasa bajas 4 kHz

% Mostrar constantes del nuevo filtro
disp('Coeficientes del filtro pasa bajas de 4 kHz (Butterworth 2do orden):');
disp('Numerador (b):'); disp(b3);
disp('Denominador (a):'); disp(a3);

% Generar señal para gráficas (mezcla de 20 Hz y 2 kHz)
signal = [sinetone(fc1, sf, 1, 1) + sinetone(fc2, sf, 1, 1)] * 2.5/2;

% Configuración de gráficas
clf
figure(1)

% Gráfica 1: Señal original
subplot(5, 1, 1)
plot(signal, ';Señal original (20 Hz + 2 kHz);')
axis([0 fc1*200])
grid on

% Gráfica 2: Filtro pasa bajas 20 Hz
subplot(5, 1, 2)
plot(filtered1(:, 2), ';Filtro pasa bajas 20 Hz;')
axis([0 fc1*200])
grid on

% Gráfica 3: Filtro pasa altas 2 kHz
subplot(5, 1, 3)
plot(filtered2(:, 2), ';Filtro pasa altas 2 kHz;')
axis([0 fc1*200])
grid on

% Gráfica 4: Nuevo filtro pasa bajas 4 kHz (vista amplia)
subplot(5, 1, 4)
plot(filtered3(:, 2), ';Filtro pasa bajas 4 kHz;', 'Color', [0 0.5 0])
axis([0 fc1*200])
grid on

% Gráfica 5: Nuevo filtro pasa bajas 4 kHz (vista detalle)
subplot(5, 1, 5)
plot(filtered3(:, 2), ';Detalle filtro 4 kHz;', 'Color', [0 0.5 0])
axis([0 fc1*5])
grid on

% Espectro de frecuencias (opcional)
figure(2)
N = length(signal);
f = (0:N-1)*(sf/N);
fft_original = abs(fft(signal));
fft_filtered = abs(fft(filtered3(:,2)));

semilogy(f(1:N/2), fft_original(1:N/2), 'b', f(1:N/2), fft_filtered(1:N/2), 'g')
title('Espectro de frecuencia (Original vs Filtro 4 kHz)')
xlabel('Frecuencia (Hz)')
ylabel('Magnitud (log)')
legend('Original', 'Pasa bajas 4 kHz')
grid on
axis([0 sf2 1e-1 1e3])
axis([0 sf2 1e-1 1e3])
