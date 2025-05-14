import numpy as np
from scipy.io import wavfile
import matplotlib.pyplot as plt
from scipy import signal

# Configuración
fs = 44100  # Frecuencia de muestreo (debe coincidir con tu ecualizador)
duration = 3  # Duración en segundos
output_folder = "test_audios"

# Crear carpeta si no existe
import os
os.makedirs(output_folder, exist_ok=True)

def generate_sine_wave(freq, duration=duration, fs=fs):
    """Genera un tono sinusoidal puro"""
    t = np.linspace(0, duration, int(fs * duration), False)
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    return audio

def generate_white_noise(duration=duration, fs=fs):
    """Genera ruido blanco (todo el espectro de frecuencias)"""
    return np.random.uniform(-0.5, 0.5, size=int(fs * duration))

def generate_chirp(start_freq, end_freq, duration=duration, fs=fs):
    """Genera un chirp (frecuencia que varía linealmente)"""
    t = np.linspace(0, duration, int(fs * duration), False)
    audio = 0.5 * signal.chirp(t, start_freq, duration, end_freq)
    return audio

def generate_multitone(frequencies, duration=duration, fs=fs):
    """Genera una señal con múltiples tonos simultáneos"""
    t = np.linspace(0, duration, int(fs * duration), False)
    audio = np.zeros_like(t)
    for freq in frequencies:
        audio += 0.2 * np.sin(2 * np.pi * freq * t)
    return audio

def save_audio(filename, audio, fs=fs):
    """Guarda el audio como archivo WAV"""
    # Normalizar a int16
    audio_int16 = np.int16(audio * 32767)
    wavfile.write(filename, fs, audio_int16)
    print(f"Audio guardado: {filename}")

def plot_audio(audio, title, fs=fs):
    """Muestra la señal y su espectro"""
    plt.figure(figsize=(12, 6))
    
    # Señal temporal
    plt.subplot(2, 1, 1)
    time = np.linspace(0, len(audio)/fs, len(audio))
    plt.plot(time[:1000], audio[:1000])  # Mostrar solo los primeros 1000 samples
    plt.title(f"{title} (Primeros 1000 samples)")
    plt.xlabel("Tiempo (s)")
    plt.ylabel("Amplitud")
    
    # Espectro
    plt.subplot(2, 1, 2)
    fft = np.fft.fft(audio)
    freqs = np.fft.fftfreq(len(audio), 1/fs)
    plt.plot(freqs[:len(freqs)//2], np.abs(fft[:len(fft)//2]))
    plt.title("Espectro de frecuencia")
    plt.xlabel("Frecuencia (Hz)")
    plt.ylabel("Magnitud")
    plt.xlim(0, 20000)
    
    plt.tight_layout()
    plt.show()

# Generar audios de prueba
test_audios = {
    # Tonos puros
    "sine_440Hz.wav": generate_sine_wave(440),
    "sine_1000Hz.wav": generate_sine_wave(1000),
    "sine_5000Hz.wav": generate_sine_wave(5000),
    "sine_10000Hz.wav": generate_sine_wave(10000),
    
    # Ruido
    "white_noise.wav": generate_white_noise(),
    
    # Chirps
    "chirp_100-10000Hz.wav": generate_chirp(100, 10000),
    "chirp_5000-1000Hz.wav": generate_chirp(5000, 1000),  # Chirp descendente
    
    # Multitonos
    "multitone_250-1000-4000Hz.wav": generate_multitone([250, 1000, 4000]),
    "multitone_50-500-5000-15000Hz.wav": generate_multitone([50, 500, 5000, 15000]),
}

# Generar y guardar todos los audios
for filename, audio in test_audios.items():
    full_path = os.path.join(output_folder, filename)
    save_audio(full_path, audio)
    
    # Mostrar gráficos para los primeros 4 audios
    if list(test_audios.keys()).index(filename) < 4:
        plot_audio(audio, filename)

print("\n¡Todos los audios de prueba han sido generados!")
print(f"Puedes encontrarlos en la carpeta: '{output_folder}'")