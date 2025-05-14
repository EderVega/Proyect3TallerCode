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

# Configuración inicial mejorada
fs = 44100  # Frecuencia de muestreo estándar
block_size = 2048  # Tamaño de bloque aumentado para mejor rendimiento
stream = None
audio_file = None
file_position = 0
is_playing_file = False
last_audio_chunk = np.zeros(block_size)
volume = 1.0  # Volumen inicial al 100%

# Diseño de filtros más eficiente usando sos
def create_filter_sos(order, cutoff, btype, fs=fs):
    return signal.butter(order, cutoff/(fs/2), btype=btype, output='sos')

# Filtros en formato SOS (Second-Order Sections) para mejor estabilidad
sos_low = create_filter_sos(4, 4000, 'low')
sos_high = create_filter_sos(4, 8000, 'high')
sos_band = create_filter_sos(4, [5000, 12000], 'bandpass')
sos_stop = create_filter_sos(4, [4000, 8000], 'bandstop')

# Variables globales para el filtro personalizado
fc_custom = 4000
sos_custom = create_filter_sos(2, fc_custom, 'low')

def apply_filters(audio_data):
    """Aplica todos los filtros activos usando sosfilt para mejor eficiencia"""
    global fc_custom, sos_custom
    audio = audio_data.copy()
    
    # Aplicar filtros en cascada solo si están activos
    if var_lowpass.get():
        audio = signal.sosfilt(sos_low, audio, axis=0)
    if var_highpass.get():
        audio = signal.sosfilt(sos_high, audio, axis=0)
    if var_bandpass.get():
        audio = signal.sosfilt(sos_band, audio, axis=0)
    if var_bandstop.get():
        audio = signal.sosfilt(sos_stop, audio, axis=0)
    if var_custom.get():
        new_fc = slider_fc.get()
        if new_fc != fc_custom:
            fc_custom = new_fc
            sos_custom = create_filter_sos(2, fc_custom, 'low')
        audio = signal.sosfilt(sos_custom, audio, axis=0)
    
    return audio * volume  # Aplica ganancia de volumen

def audio_callback(indata, outdata, frames, time, status):
    """Callback optimizado para procesamiento de audio"""
    global file_position, audio_file, is_playing_file, last_audio_chunk
    
    if status:
        print(f"Error en stream: {status}")
        outdata[:] = np.zeros((frames, 1))
        return
    
    try:
        if is_playing_file and audio_file is not None:
            remaining_samples = len(audio_file) - file_position
            if remaining_samples <= 0:
                outdata[:] = np.zeros((frames, 1))
                is_playing_file = False
                btn_play_file.config(text="Reproducir Archivo")
                return
            
            chunk = audio_file[file_position:file_position + frames]
            file_position += len(chunk)
            
            if len(chunk) < frames:
                chunk = np.pad(chunk, (0, frames - len(chunk)), 'constant')
            
            processed_audio = apply_filters(chunk)
            outdata[:] = processed_audio.reshape(-1, 1)
            last_audio_chunk = processed_audio
        else:
            if indata.any():
                processed_audio = apply_filters(indata[:, 0])
                outdata[:] = processed_audio.reshape(-1, 1)
                last_audio_chunk = processed_audio
            else:
                outdata[:] = np.zeros((frames, 1))
    except Exception as e:
        print(f"Error en callback: {e}")
        outdata[:] = np.zeros((frames, 1))

def load_audio_file():
    """Carga archivos de audio con mejor manejo de errores"""
    global audio_file, file_position, is_playing_file
    
    filepath = filedialog.askopenfilename(
        filetypes=[("Archivos WAV", "*.wav"), ("Todos los archivos", "*.*")]
    )
    
    if not filepath:
        return
    
    try:
        file_fs, data = wavfile.read(filepath)
        
        # Convertir a mono si es estéreo
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Normalización mejorada
        data = data.astype(np.float32)
        max_val = np.max(np.abs(data))
        if max_val > 0:
            data /= max_val
        
        # Resample si es necesario
        if file_fs != fs:
            num_samples = int(len(data) * fs / file_fs)
            data = signal.resample(data, num_samples)
        
        audio_file = data
        file_position = 0
        lbl_file.config(text=f"Archivo: {os.path.basename(filepath)}")
        btn_play_file.config(state=tk.NORMAL)
        messagebox.showinfo("Éxito", "Archivo cargado correctamente")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")

def toggle_file_playback():
    """Control de reproducción con mejor manejo de estados"""
    global is_playing_file
    is_playing_file = not is_playing_file
    btn_play_file.config(text="Detener Archivo" if is_playing_file else "Reproducir Archivo")

def toggle_live_processing():
    """Control de procesamiento en vivo con manejo de errores"""
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
            messagebox.showerror("Error", f"No se pudo iniciar el micrófono:\n{e}")
    else:
        try:
            stream.stop()
            stream = None
            btn_live.config(text="Iniciar Micrófono")
        except Exception as e:
            print(f"Error al detener stream: {e}")

def export_audio():
    """Exportación de audio con validaciones"""
    if audio_file is None:
        messagebox.showwarning("Advertencia", "No hay archivo cargado para exportar")
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
        messagebox.showinfo("Éxito", "Audio exportado correctamente")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar el audio:\n{e}")

def update_volume(val):
    """Control de volumen con validación"""
    global volume
    try:
        volume = float(val)
        lbl_volume.config(text=f"Volumen: {int(volume * 100)}%")
    except ValueError:
        pass

def update_spectrum():
    """Visualización de espectro optimizada"""
    if np.any(last_audio_chunk):
        try:
            fft_data = np.abs(np.fft.rfft(last_audio_chunk))
            max_val = np.max(fft_data)
            if max_val > 0:
                fft_data /= max_val
            freqs = np.fft.rfftfreq(len(last_audio_chunk), 1/fs)
            line.set_data(freqs, fft_data)
            ax.set_xlim(0, fs/2)
            ax.set_ylim(0, 1)
            canvas.draw()
        except Exception as e:
            print(f"Error al actualizar espectro: {e}")
    root.after(100, update_spectrum)

# Interfaz gráfica mejorada
root = tk.Tk()
root.title("Ecualizador Digital Avanzado")
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
btn_play_file = ttk.Button(file_frame, text="Reproducir Archivo", 
                         command=toggle_file_playback, state=tk.DISABLED)
btn_play_file.pack(side=tk.LEFT, padx=5)
lbl_file = ttk.Label(file_frame, text="Ningún archivo cargado")
lbl_file.pack(side=tk.LEFT, padx=5)

# Sección de micrófono
live_frame = ttk.LabelFrame(main_frame, text="Procesamiento en Vivo", padding="10")
live_frame.pack(fill=tk.X, pady=5)
btn_live = ttk.Button(live_frame, text="Iniciar Micrófono", 
                     command=toggle_live_processing)
btn_live.pack()

# Sección de volumen
volume_frame = ttk.LabelFrame(main_frame, text="Volumen", padding="10")
volume_frame.pack(fill=tk.X, pady=5)
slider_volume = ttk.Scale(volume_frame, from_=0.0, to=1.0, orient="horizontal", 
                         command=update_volume)
slider_volume.set(1.0)
slider_volume.pack(fill=tk.X, padx=5, pady=2)
lbl_volume = ttk.Label(volume_frame, text="Volumen: 100%")
lbl_volume.pack()

# Sección de filtros
filters_frame = ttk.LabelFrame(main_frame, text="Filtros", padding="10")
filters_frame.pack(fill=tk.BOTH, expand=True, pady=5)

def create_filter_control(parent, text, var):
    """Función auxiliar para crear controles de filtro"""
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
ttk.Checkbutton(custom_frame, text="Pasa Bajas Configurable", 
               variable=var_custom).pack(side=tk.LEFT)
ttk.Label(custom_frame, text="Frecuencia (Hz):").pack(side=tk.LEFT, padx=5)
slider_fc = ttk.Scale(custom_frame, from_=1000, to=8000, orient="horizontal")
slider_fc.set(fc_custom)
slider_fc.pack(side=tk.LEFT, expand=True, fill=tk.X)

# Botón de exportación
btn_export = ttk.Button(main_frame, text="Exportar Audio Procesado", 
                       command=export_audio)
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

# Iniciar actualización del espectro
update_spectrum()

# Manejo de cierre de ventana
def on_closing():
    if stream is not None:
        stream.stop()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()