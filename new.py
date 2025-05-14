"""
import numpy as np
import sounddevice as sd
from scipy import signal
import tkinter as tk
from tkinter import ttk

# Configuración inicial
fs = 44100
block_size = 1024
stream = None

# Diseño de filtros
fc_low = 4000
b_low, a_low = signal.butter(2, fc_low / (fs / 2), 'low')

fc_high = 8000
b_high, a_high = signal.butter(2, fc_high / (fs / 2), 'high')

low_band = 5000
high_band = 12000
b_band, a_band = signal.butter(2, [low_band / (fs / 2), high_band / (fs / 2)], 'bandpass')

low_stop = 4000
high_stop = 8000
b_stop, a_stop = signal.butter(2, [low_stop / (fs / 2), high_stop / (fs / 2)], 'bandstop')

fc_custom = 4000
b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')

# Función de procesamiento de audio
def audio_callback(indata, outdata, frames, time, status):
    audio = indata.copy()
    
    if var_highpass.get() and var_bandpass.get():
        audio = signal.lfilter(b_high, a_high, audio, axis=0)
        audio = signal.lfilter(b_band, a_band, audio, axis=0)
    else:
        if var_lowpass.get():
            audio = signal.lfilter(b_low, a_low, audio, axis=0)
        if var_highpass.get():
            audio = signal.lfilter(b_high, a_high, audio, axis=0)
        if var_bandpass.get():
            audio = signal.lfilter(b_band, a_band, audio, axis=0)
        if var_bandstop.get():
            audio = signal.lfilter(b_stop, a_stop, audio, axis=0)
        if var_custom.get():
            global b_custom, a_custom
            new_fc = slider_fc.get()
            if new_fc != fc_custom:
                fc_custom = new_fc
                b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')
            audio = signal.lfilter(b_custom, a_custom, audio, axis=0)
    
    outdata[:] = audio

# Interfaz gráfica corregida
root = tk.Tk()
root.title("Ecualizador Digital - ITCR")
root.geometry("500x600")

# Variables de control
var_lowpass = tk.BooleanVar()
var_highpass = tk.BooleanVar()
var_bandpass = tk.BooleanVar()
var_bandstop = tk.BooleanVar()
var_custom = tk.BooleanVar()

volume_low = tk.DoubleVar(value=1.0)
volume_high = tk.DoubleVar(value=1.0)
volume_band = tk.DoubleVar(value=1.0)
volume_stop = tk.DoubleVar(value=1.0)
volume_custom = tk.DoubleVar(value=1.0)

# Usaremos solo pack() para todo el diseño
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# Función modificada para usar solo pack()
def create_filter_control(parent, text, var, volume_var):
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, pady=2)
    
    cb = ttk.Checkbutton(frame, text=text, variable=var)
    cb.pack(side=tk.LEFT, padx=5)
    
    scale = ttk.Scale(frame, from_=0, to=1, variable=volume_var, orient="horizontal")
    scale.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)

# Controles de filtro
ttk.Label(main_frame, text="Filtros", font=('Arial', 12, 'bold')).pack(pady=5)
create_filter_control(main_frame, "Pasa Bajas (<4kHz)", var_lowpass, volume_low)
create_filter_control(main_frame, "Pasa Altas (>8kHz)", var_highpass, volume_high)
create_filter_control(main_frame, "Pasa Banda (5kHz-12kHz)", var_bandpass, volume_band)
create_filter_control(main_frame, "Rechaza Banda (4kHz-8kHz)", var_bandstop, volume_stop)
create_filter_control(main_frame, "Pasa Bajas Configurable", var_custom, volume_custom)

# Control de frecuencia
ttk.Label(main_frame, text="Frecuencia de Corte Pasa Bajas:", font=('Arial', 10)).pack(pady=(10,0))
slider_fc = ttk.Scale(main_frame, from_=1000, to=8000, orient="horizontal")
slider_fc.set(4000)
slider_fc.pack(fill=tk.X, padx=20, pady=5)

# Botón de control
btn = ttk.Button(main_frame, text="Iniciar Procesamiento", command=lambda: start_stop_processing())
btn.pack(pady=20)

def start_stop_processing():
    global stream
    if stream is None:
        stream = sd.Stream(
            callback=audio_callback,
            blocksize=block_size,
            samplerate=fs,
            channels=1
        )
        stream.start()
        btn.config(text="Detener Procesamiento")
    else:
        stream.stop()
        stream = None
        btn.config(text="Iniciar Procesamiento")

root.mainloop()

"""
import numpy as np
import sounddevice as sd
from scipy import signal
import tkinter as tk
from tkinter import ttk, filedialog
from scipy.io import wavfile
import os

# Configuración inicial
fs = 44100
block_size = 1024
stream = None
audio_file = None
file_position = 0
is_playing_file = False

# Variables globales para los filtros
fc_custom = 4000
b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')

# Diseño de los filtros
b_low, a_low = signal.butter(2, 4000 / (fs / 2), 'low')
b_high, a_high = signal.butter(2, 8000 / (fs / 2), 'high')
b_band, a_band = signal.butter(2, [5000 / (fs / 2), 12000 / (fs / 2)], 'bandpass')
b_stop, a_stop = signal.butter(2, [4000 / (fs / 2), 8000 / (fs / 2)], 'bandstop')

def apply_filters(audio_data):
    """Aplica los filtros seleccionados a los datos de audio"""
    global fc_custom, b_custom, a_custom
    
    audio = audio_data.copy()
    
    if var_highpass.get() and var_bandpass.get():
        audio = signal.lfilter(b_high, a_high, audio, axis=0)
        audio = signal.lfilter(b_band, a_band, audio, axis=0)
    else:
        if var_lowpass.get():
            audio = signal.lfilter(b_low, a_low, audio, axis=0)
        if var_highpass.get():
            audio = signal.lfilter(b_high, a_high, audio, axis=0)
        if var_bandpass.get():
            audio = signal.lfilter(b_band, a_band, audio, axis=0)
        if var_bandstop.get():
            audio = signal.lfilter(b_stop, a_stop, audio, axis=0)
        if var_custom.get():
            new_fc = slider_fc.get()
            if new_fc != fc_custom:
                fc_custom = new_fc
                b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')
            audio = signal.lfilter(b_custom, a_custom, audio, axis=0)
    
    return audio

def audio_callback(indata, outdata, frames, time, status):
    """Callback para el procesamiento en tiempo real"""
    global file_position, audio_file, is_playing_file
    
    if is_playing_file and audio_file is not None:
        # Procesamiento de archivo de audio
        remaining_samples = len(audio_file) - file_position
        if remaining_samples == 0:
            outdata[:] = np.zeros((frames, 1))
            return
            
        samples_to_process = min(frames, remaining_samples)
        chunk = audio_file[file_position:file_position + samples_to_process]
        file_position += samples_to_process
        
        if len(chunk) < frames:
            chunk = np.pad(chunk, (0, frames - len(chunk)), 'constant')

        
        processed_audio = apply_filters(chunk)
        outdata[:] = processed_audio
    else:
        # Procesamiento de micrófono
        processed_audio = apply_filters(indata)
        outdata[:] = processed_audio

def load_audio_file():
    """Carga un archivo de audio para procesamiento"""
    global audio_file, file_position, is_playing_file
    
    filepath = filedialog.askopenfilename(
        filetypes=[("Archivos WAV", "*.wav"), ("Todos los archivos", "*.*")]
    )
    
    if filepath:
        try:
            file_fs, data = wavfile.read(filepath)
            if file_fs != fs:
                data = signal.resample(data, int(len(data) * fs / file_fs))
            
            # Convertir a mono si es estéreo
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            # Normalizar
            audio_file = data / np.max(np.abs(data))
            file_position = 0
            lbl_file.config(text=f"Archivo: {os.path.basename(filepath)}")
            btn_play_file.config(state=tk.NORMAL)
        except Exception as e:
            print(f"Error al cargar archivo: {e}")

def toggle_file_playback():
    """Inicia/detiene la reproducción del archivo"""
    global is_playing_file
    
    is_playing_file = not is_playing_file
    if is_playing_file:
        btn_play_file.config(text="Detener Archivo")
    else:
        btn_play_file.config(text="Reproducir Archivo")

def toggle_live_processing():
    """Inicia/detiene el procesamiento en vivo"""
    global stream
    
    if stream is None:
        try:
            stream = sd.Stream(
                callback=audio_callback,
                blocksize=block_size,
                samplerate=fs,
                channels=1
            )
            stream.start()
            btn_live.config(text="Detener Micrófono")
        except Exception as e:
            print(f"No se pudo iniciar el stream: {e}")
    else:
        stream.stop()
        stream = None
        btn_live.config(text="Iniciar Micrófono")

# Interfaz gráfica
root = tk.Tk()
root.title("Ecualizador Digital - ITCR")
root.geometry("600x700")

# Variables de control
var_lowpass = tk.BooleanVar()
var_highpass = tk.BooleanVar()
var_bandpass = tk.BooleanVar()
var_bandstop = tk.BooleanVar()
var_custom = tk.BooleanVar()

# Marco principal
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# Sección de archivos
file_frame = ttk.LabelFrame(main_frame, text="Archivo de Audio", padding="10")
file_frame.pack(fill=tk.X, pady=5)

btn_load = ttk.Button(file_frame, text="Cargar Archivo", command=load_audio_file)
btn_load.pack(side=tk.LEFT, padx=5)

btn_play_file = ttk.Button(file_frame, text="Reproducir Archivo", 
                         command=toggle_file_playback, state=tk.DISABLED)
btn_play_file.pack(side=tk.LEFT, padx=5)

lbl_file = ttk.Label(file_frame, text="Ningún archivo cargado")
lbl_file.pack(side=tk.LEFT, padx=5)

# Sección de procesamiento en vivo
live_frame = ttk.LabelFrame(main_frame, text="Procesamiento en Vivo", padding="10")
live_frame.pack(fill=tk.X, pady=5)

btn_live = ttk.Button(live_frame, text="Iniciar Micrófono", 
                     command=toggle_live_processing)
btn_live.pack()

# Controles de filtros
filters_frame = ttk.LabelFrame(main_frame, text="Filtros", padding="10")
filters_frame.pack(fill=tk.BOTH, expand=True, pady=5)

def create_filter_control(parent, text, var):
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, pady=2)
    
    ttk.Checkbutton(frame, text=text, variable=var).pack(side=tk.LEFT)
    return frame

# Filtros individuales
create_filter_control(filters_frame, "Pasa Bajas (<4kHz)", var_lowpass)
create_filter_control(filters_frame, "Pasa Altas (>8kHz)", var_highpass)
create_filter_control(filters_frame, "Pasa Banda (5k-12kHz)", var_bandpass)
create_filter_control(filters_frame, "Rechaza Banda (4k-8kHz)", var_bandstop)

# Filtro configurable
custom_frame = ttk.Frame(filters_frame)
custom_frame.pack(fill=tk.X, pady=5)

ttk.Checkbutton(custom_frame, text="Pasa Bajas Configurable", 
               variable=var_custom).pack(side=tk.LEFT)

ttk.Label(custom_frame, text="Frecuencia (Hz):").pack(side=tk.LEFT, padx=5)
slider_fc = ttk.Scale(custom_frame, from_=1000, to=8000, 
                     orient="horizontal")
slider_fc.set(fc_custom)
slider_fc.pack(side=tk.LEFT, expand=True, fill=tk.X)

# Botón de exportación
def export_audio():
    if audio_file is None:
        return
        
    filepath = filedialog.asksaveasfilename(
        defaultextension=".wav",
        filetypes=[("Archivos WAV", "*.wav")]
    )
    
    if filepath:
        processed_audio = apply_filters(audio_file)
        wavfile.write(filepath, fs, processed_audio)

btn_export = ttk.Button(main_frame, text="Exportar Audio Procesado", 
                       command=export_audio)
btn_export.pack(pady=10)

root.mainloop()