import numpy as np
import sounddevice as sd
from scipy import signal
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scipy.io import wavfile
import os
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Configuración inicial
fs = 44100  # Frecuencia de muestreo
block_size = 1024  # Tamaño del bloque de audio
stream = None  # Stream de audio
audio_file = None  # Archivo de audio cargado
file_position = 0  # Posición en el archivo
is_playing_file = False  # Estado de reproducción
last_audio_chunk = np.zeros(block_size)  # Último chunk de audio (para el espectro)
volume = 1.0  # Volumen (0.0 a 1.0)
latency = 0.1 # Latencia en segundos
# Diseño de los filtros
b_low, a_low = signal.butter(4, 4000 / (fs / 2), 'low')  # Pasa-bajos (4kHz)
b_high, a_high = signal.butter(4, 8000 / (fs / 2), 'high')  # Pasa-altos (8kHz)
b_band, a_band = signal.butter(4, [5000 / (fs / 2), 12000 / (fs / 2)], 'bandpass')  # Pasa-banda (5k-12kHz)
b_stop, a_stop = signal.butter(4, [4000 / (fs / 2), 8000 / (fs / 2)], 'bandstop')  # Rechaza-banda (4k-8kHz)
fc_custom = 4000  # Frecuencia de corte personalizada (inicial: 4kHz)
b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')  # Filtro personalizado

# --- Funciones principales ---
def apply_filters(audio_data):
    """Aplica todos los filtros activos en cascada."""
    global fc_custom, b_custom, a_custom
    
    try:
        # Convertimos a float32 para mejor rendimiento
        audio = audio_data.astype(np.float32).copy()

        # Aplicamos los filtros solo si hay señal
        if not np.any(audio):
            return audio

        # Aplicamos los filtros en orden
        if var_lowpass.get():
            audio = signal.filtfilt(b_low, a_low, audio)
        if var_highpass.get():
            audio = signal.filtfilt(b_high, a_high, audio)
        if var_bandpass.get():
            audio = signal.filtfilt(b_band, a_band, audio)
        if var_bandstop.get():
            audio = signal.filtfilt(b_stop, a_stop, audio)
        if var_custom.get():
            new_fc = slider_fc.get()
            if new_fc != fc_custom:
                fc_custom = new_fc
                b_custom, a_custom = signal.butter(2, fc_custom / (fs / 2), 'low')
            audio = signal.filtfilt(b_custom, a_custom, audio)

        # Aplicamos el volumen y prevenimos clipping
        return np.clip(audio * volume, -1.0, 1.0)
    
    except Exception as e:
        print(f"Error en apply_filters: {e}")
        return audio_data
    
def audio_callback(indata, outdata, frames, time, status):
    """Callback para procesamiento de audio en tiempo real."""
    global file_position, audio_file, is_playing_file, last_audio_chunk

    if status:
        # Solo imprimimos errores críticos
        if status.input_overflow or status.output_underflow:
            return
        print(f"Error crítico en el stream: {status}")

    try:
        if is_playing_file and audio_file is not None:
            remaining_samples = len(audio_file) - file_position
            if remaining_samples <= 0:
                outdata.fill(0)
                is_playing_file = False
                root.after(0, lambda: btn_play_file.config(text="Reproducir Archivo"))
                return
            
            chunk = audio_file[file_position:file_position + frames]
            file_position += len(chunk)
            if len(chunk) < frames:
                chunk = np.pad(chunk, (0, frames - len(chunk)), 'constant')
            processed_audio = apply_filters(chunk)
            
        else:
            if np.any(indata):
                processed_audio = apply_filters(indata[:, 0])
            else:
                outdata.fill(0)
                return

        # Prevenir clipping
        processed_audio = np.clip(processed_audio, -1.0, 1.0)
        outdata[:] = processed_audio.reshape(-1, 1)
        last_audio_chunk = processed_audio

    except Exception as e:
        outdata.fill(0)
        print(f"Error en el procesamiento de audio: {e}")

def load_audio_file():
    """Carga un archivo de audio y lo normaliza."""
    global audio_file, file_position, is_playing_file
    filepath = filedialog.askopenfilename(filetypes=[("Archivos WAV", "*.wav"), ("Todos los archivos", "*.*")])
    
    if not filepath:
        return

    try:
        file_fs, data = wavfile.read(filepath)
        
        # Convierte a mono si es estéreo
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Normaliza a [-1, 1] y ajusta la frecuencia de muestreo si es necesario
        data = data.astype(np.float32)
        data /= np.max(np.abs(data)) if np.max(np.abs(data)) > 0 else 1.0
        
        if file_fs != fs:
            data = signal.resample(data, int(len(data) * fs / file_fs))
        
        audio_file = data
        file_position = 0
        lbl_file.config(text=f"Archivo: {os.path.basename(filepath)}")
        btn_play_file.config(state=tk.NORMAL)
        messagebox.showinfo("Éxito", "Archivo cargado correctamente.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el archivo: {e}")

def toggle_file_playback():
    """Inicia/detiene la reproducción del archivo."""
    global is_playing_file
    is_playing_file = not is_playing_file
    btn_play_file.config(text="Detener Archivo" if is_playing_file else "Reproducir Archivo")

def toggle_live_processing():
    """Inicia/detiene el procesamiento en vivo del micrófono."""
    global stream
    if stream is None:
        try:
            stream = sd.Stream(
                callback=audio_callback,
                blocksize=block_size,
                samplerate=fs,
                channels=1,
                latency=latency,  # Añadimos latencia
                device=None,  # Usar dispositivo por defecto
                dtype=np.float32  # Especificamos el tipo de datos
            )
            stream.start()
            btn_live.config(text="Detener Micrófono")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar el micrófono: {e}")
    else:
        try:
            stream.stop()
            stream.close()  # Agregamos close() para liberar recursos
            stream = None
            btn_live.config(text="Iniciar Micrófono")
        except Exception as e:
            messagebox.showerror("Error", f"Error al detener el micrófono: {e}")

def export_audio():
    """Exporta el audio procesado a un archivo WAV."""
    if audio_file is None:
        messagebox.showwarning("Advertencia", "No hay ningún archivo cargado.")
        return

    filepath = filedialog.asksaveasfilename(
        defaultextension=".wav",
        filetypes=[("Archivos WAV", "*.wav")]
    )
    
    if not filepath:
        return

    try:
        processed_audio = apply_filters(audio_file)
        wavfile.write(filepath, fs, processed_audio.astype(np.float32))
        messagebox.showinfo("Éxito", "Audio exportado correctamente.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar el audio: {e}")

def update_volume(val):
    """Actualiza el volumen global."""
    global volume
    volume = float(val)
    lbl_volume.config(text=f"Volumen: {int(volume * 100)}%")

def update_spectrum():
    """Actualiza el espectro de frecuencia en tiempo real."""
    if np.any(last_audio_chunk):
        fft_data = np.abs(np.fft.rfft(last_audio_chunk))
        fft_data /= np.max(fft_data) if np.max(fft_data) > 0 else 1.0
        freqs = np.fft.rfftfreq(len(last_audio_chunk), 1/fs)
        line.set_data(freqs, fft_data)
        ax.set_xlim(0, fs/2)
        ax.set_ylim(0, 1)
        canvas.draw()
    root.after(100, update_spectrum)

# --- Interfaz gráfica ---
root = tk.Tk()
root.title("Ecualizador Digital - ITCR")
root.geometry("800x800")

# Variables de control
var_lowpass = tk.BooleanVar()
var_highpass = tk.BooleanVar()
var_bandpass = tk.BooleanVar()
var_bandstop = tk.BooleanVar()
var_custom = tk.BooleanVar()

# Frame principal
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=tk.BOTH, expand=True)

# Sección de archivo
file_frame = ttk.LabelFrame(main_frame, text="Archivo de Audio", padding="10")
file_frame.pack(fill=tk.X, pady=5)
btn_load = ttk.Button(file_frame, text="Cargar Archivo", command=load_audio_file)
btn_load.pack(side=tk.LEFT, padx=5)
btn_play_file = ttk.Button(file_frame, text="Reproducir Archivo", command=toggle_file_playback, state=tk.DISABLED)
btn_play_file.pack(side=tk.LEFT, padx=5)
lbl_file = ttk.Label(file_frame, text="Ningún archivo cargado")
lbl_file.pack(side=tk.LEFT, padx=5)

# Sección de micrófono
live_frame = ttk.LabelFrame(main_frame, text="Procesamiento en Vivo", padding="10")
live_frame.pack(fill=tk.X, pady=5)
btn_live = ttk.Button(live_frame, text="Iniciar Micrófono", command=toggle_live_processing)
btn_live.pack()

# Sección de volumen
volume_frame = ttk.LabelFrame(main_frame, text="Volumen", padding="10")
volume_frame.pack(fill=tk.X, pady=5)

lbl_volume = ttk.Label(volume_frame, text="Volumen: 100%")  # <-- Mueve esta línea antes
lbl_volume.pack()

slider_volume = ttk.Scale(volume_frame, from_=0.0, to=1.0, orient="horizontal", command=update_volume)
slider_volume.set(1.0)
slider_volume.pack(fill=tk.X, padx=5, pady=2)


# Sección de filtros
filters_frame = ttk.LabelFrame(main_frame, text="Filtros", padding="10")
filters_frame.pack(fill=tk.BOTH, expand=True, pady=5)

def create_filter_control(parent, text, var):
    """Crea un checkbox para un filtro."""
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, pady=2)
    ttk.Checkbutton(frame, text=text, variable=var).pack(side=tk.LEFT)
    return frame

create_filter_control(filters_frame, "Pasa Bajas (<4kHz)", var_lowpass)
create_filter_control(filters_frame, "Pasa Altas (>8kHz)", var_highpass)
create_filter_control(filters_frame, "Pasa Banda (5k-12kHz)", var_bandpass)
create_filter_control(filters_frame, "Rechaza Banda (4k-8kHz)", var_bandstop)

# Filtro personalizado
custom_frame = ttk.Frame(filters_frame)
custom_frame.pack(fill=tk.X, pady=5)
ttk.Checkbutton(custom_frame, text="Pasa Bajas Configurable", variable=var_custom).pack(side=tk.LEFT)
ttk.Label(custom_frame, text="Frecuencia (Hz):").pack(side=tk.LEFT, padx=5)
slider_fc = ttk.Scale(custom_frame, from_=1000, to=8000, orient="horizontal")
slider_fc.set(fc_custom)
slider_fc.pack(side=tk.LEFT, expand=True, fill=tk.X)

# Botón de exportación
btn_export = ttk.Button(main_frame, text="Exportar Audio Procesado", command=export_audio)
btn_export.pack(pady=10)

# Visualizador de espectro
spectrum_frame = ttk.LabelFrame(main_frame, text="Espectro de Frecuencia", padding="10")
spectrum_frame.pack(fill=tk.BOTH, expand=True)

fig = Figure(figsize=(6, 3), dpi=100)
ax = fig.add_subplot(111)
line, = ax.plot([], [])
ax.set_xlim(0, fs / 2)
ax.set_ylim(0, 1)
ax.set_xlabel("Frecuencia (Hz)")
ax.set_ylabel("Magnitud")
ax.grid(True)

canvas = FigureCanvasTkAgg(fig, master=spectrum_frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Inicia la actualización del espectro
update_spectrum()

root.mainloop()