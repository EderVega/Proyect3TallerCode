import numpy as np
import sounddevice as sd
from scipy import signal
import tkinter as tk
from tkinter import ttk

# =============================================================================
# Configuración inicial
# =============================================================================
fs = 44100  # Frecuencia de muestreo (Hz)
block_size = 1024  # Tamaño del bloque de audio

# =============================================================================
# Diseño de los filtros (todos de 2do orden)
# =============================================================================
# Filtro Pasa Bajas (<4kHz)
fc_low = 4000
b_low, a_low = signal.butter(2, fc_low / (fs / 2), 'low')

# Filtro Pasa Altas (>8kHz)
fc_high = 8000
b_high, a_high = signal.butter(2, fc_high / (fs / 2), 'high')

# Filtro Pasa Banda (5kHz-12kHz)
low_band = 5000
high_band = 12000
b_band, a_band = signal.butter(2, [low_band / (fs / 2), high_band / (fs / 2)], 'bandpass')

# Filtro Rechaza Banda (4kHz-8kHz)
low_stop = 4000
high_stop = 8000
b_stop, a_stop = signal.butter(2, [low_stop / (fs / 2), high_stop / (fs / 2)], 'bandstop')

# Filtro Pasa Bajas Configurable (se ajusta con GUI)
fc_custom = 4000  # Valor inicial
b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')

# =============================================================================
# Función de procesamiento de audio (se llama en cada bloque)
# =============================================================================
def audio_callback(indata, outdata, frames, time, status):
    audio = indata.copy()  # Copiar la entrada para no modificarla directamente
    
    # Aplicar filtros según los selectores de la GUI
    if var_lowpass.get():  # Si el Pasa Bajas está activado
        audio = signal.lfilter(b_low, a_low, audio, axis=0)
    
    if var_highpass.get():  # Si el Pasa Altas está activado
        audio = signal.lfilter(b_high, a_high, audio, axis=0)
    
    if var_bandpass.get():  # Si el Pasa Banda está activado
        audio = signal.lfilter(b_band, a_band, audio, axis=0)
    
    if var_bandstop.get():  # Si el Rechaza Banda está activado
        audio = signal.lfilter(b_stop, a_stop, audio, axis=0)
    
    if var_custom.get():  # Si el Pasa Bajas Configurable está activado
        # Recalculamos el filtro si cambió la frecuencia
        global b_custom, a_custom
        fc_custom = slider_fc.get()
        b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')
        audio = signal.lfilter(b_custom, a_custom, audio, axis=0)
    
    outdata[:] = audio  # Enviar el audio procesado a la salida

# =============================================================================
# Interfaz gráfica (GUI) con Tkinter
# =============================================================================
root = tk.Tk()
root.title("Ecualizador Digital - ITCR")

# Variables de control para los filtros
var_lowpass = tk.BooleanVar()
var_highpass = tk.BooleanVar()
var_bandpass = tk.BooleanVar()
var_bandstop = tk.BooleanVar()
var_custom = tk.BooleanVar()

# Checkboxes para activar/desactivar filtros
tk.Checkbutton(root, text="Pasa Bajas (<4kHz)", variable=var_lowpass).pack()
tk.Checkbutton(root, text="Pasa Altas (>8kHz)", variable=var_highpass).pack()
tk.Checkbutton(root, text="Pasa Banda (5kHz-12kHz)", variable=var_bandpass).pack()
tk.Checkbutton(root, text="Rechaza Banda (4kHz-8kHz)", variable=var_bandstop).pack()
tk.Checkbutton(root, text="Pasa Bajas Configurable", variable=var_custom).pack()

# Slider para ajustar la frecuencia del Pasa Bajas Configurable
slider_fc = tk.Scale(root, from_=1000, to=8000, orient="horizontal", label="Frecuencia de Corte (Hz)")
slider_fc.set(4000)  # Valor inicial
slider_fc.pack()

# Botón para iniciar/detener el procesamiento
stream = None
def start_stop():
    global stream
    if stream is None:
        stream = sd.Stream(callback=audio_callback, blocksize=block_size, samplerate=fs)
        stream.start()
        btn.config(text="Detener")
    else:
        stream.stop()
        stream = None
        btn.config(text="Iniciar")

btn = tk.Button(root, text="Iniciar", command=start_stop)
btn.pack()

root.mainloop()