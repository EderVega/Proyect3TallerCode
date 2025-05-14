import numpy as np
import sounddevice as sd
from scipy import signal
import tkinter as tk
from tkinter import ttk, filedialog
from scipy.io import wavfile
import os
import matplotlib.pyplot as plt

# Configuración inicial
fs = 44100  # Frecuencia de muestreo
block_size = 1024  # Tamaño de bloque de audio
stream = None  # Stream de audio
audio_file = None  # Archivo de audio cargado
file_position = 0  # Posición en el archivo
is_playing_file = False  # Estado de reproducción
test_mode = False  # Modo de prueba de filtros
current_test_freq = 1000  # Frecuencia de prueba actual

# Variables globales para los filtros (en formato SOS para mayor estabilidad)
fc_custom = 4000  # Frecuencia de corte inicial para el filtro configurable

# Diseño de filtros en formato SOS (Second-Order Sections)
sos_low = signal.butter(2, 4000/(fs/2), 'low', output='sos')  # Pasa bajas <4kHz
sos_high = signal.butter(2, 8000/(fs/2), 'high', output='sos')  # Pasa altas >8kHz
sos_band = signal.butter(2, [5000/(fs/2), 12000/(fs/2)], 'bandpass', output='sos')  # Pasa banda 5k-12kHz
sos_stop = signal.butter(2, [4000/(fs/2), 8000/(fs/2)], 'bandstop', output='sos')  # Rechaza banda 4k-8kHz
sos_custom = signal.butter(2, fc_custom/(fs/2), 'low', output='sos')  # Pasa bajas configurable

def apply_filters(audio_data):
    """Aplica los filtros seleccionados a los datos de audio usando SOS para mayor estabilidad"""
    global fc_custom, sos_custom
    
    audio = audio_data.copy()
    
    # Actualizar filtro personalizado si cambió la frecuencia
    if var_custom.get():
        new_fc = slider_fc.get()
        if new_fc != fc_custom:
            fc_custom = new_fc
            sos_custom = signal.butter(2, fc_custom/(fs/2), 'low', output='sos')
    
    # Aplicar filtros en cascada según selección
    if var_lowpass.get():
        audio = signal.sosfilt(sos_low, audio, axis=0)
    if var_highpass.get():
        audio = signal.sosfilt(sos_high, audio, axis=0)
    if var_bandpass.get():
        audio = signal.sosfilt(sos_band, audio, axis=0)
    if var_bandstop.get():
        audio = signal.sosfilt(sos_stop, audio, axis=0)
    if var_custom.get():
        audio = signal.sosfilt(sos_custom, audio, axis=0)
    
    # Asegurar que no hay clipping
    audio = np.clip(audio, -1.0, 1.0)
    return audio

def generate_test_tone(frequency, duration=0.1):
    """Genera un tono sinusoidal para pruebas con ventana de hanning para evitar clicks"""
    t = np.linspace(0, duration, int(fs*duration), False)
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Aplicar ventana de hanning para suavizar inicio/fin
    window = np.hanning(len(tone))
    tone = tone * window
    
    return tone.reshape(-1, 1)  # Formato adecuado para sounddevice

def audio_callback(indata, outdata, frames, time, status):
    """Callback para procesamiento de audio en tiempo real"""
    global file_position, audio_file, is_playing_file, test_mode, current_test_freq
    
    if status:
        print(f"Error en audio: {status}")
    
    if test_mode:
        # Modo prueba: generar tono de prueba
        tone = generate_test_tone(current_test_freq, frames/fs)
        processed = apply_filters(tone)
        outdata[:] = processed[:frames]  # Asegurar tamaño correcto
    elif is_playing_file and audio_file is not None:
        # Modo archivo de audio
        remaining = len(audio_file) - file_position
        if remaining == 0:
            outdata[:] = np.zeros((frames, 1))
            is_playing_file = False
            btn_play_file.config(text="Reproducir Archivo")
            return
            
        samples = min(frames, remaining)
        chunk = audio_file[file_position:file_position+samples]
        file_position += samples
        
        if len(chunk) < frames:
            chunk = np.pad(chunk, ((0, frames-len(chunk)), 'constant'))
        
        outdata[:] = apply_filters(chunk)
    else:
        # Modo micrófono en vivo
        outdata[:] = apply_filters(indata)

def load_audio_file():
    """Carga un archivo de audio para procesamiento con manejo de errores"""
    global audio_file, file_position
    
    filepath = filedialog.askopenfilename(
        filetypes=[("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("All files", "*.*")])
    if filepath:
        try:
            file_fs, data = wavfile.read(filepath)
            
            # Convertir a mono si es estéreo y normalizar
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            # Resamplear si es necesario
            if file_fs != fs:
                num_samples = int(len(data) * fs / file_fs)
                data = signal.resample(data, num_samples)
            
            # Normalizar a rango [-1, 1]
            audio_file = data / np.max(np.abs(data)) if np.max(np.abs(data)) > 0 else data
            file_position = 0
            lbl_file.config(text=os.path.basename(filepath))
            btn_play_file.config(state=tk.NORMAL)
            btn_plot.config(state=tk.NORMAL)
        except Exception as e:
            print(f"Error loading file: {e}")
            lbl_file.config(text="Error al cargar archivo")

def toggle_file_playback():
    """Controla la reproducción del archivo con reinicio al final"""
    global is_playing_file, file_position
    is_playing_file = not is_playing_file
    if is_playing_file and file_position >= len(audio_file):
        file_position = 0
    btn_play_file.config(text="Detener Archivo" if is_playing_file else "Reproducir Archivo")

def toggle_live_processing():
    """Controla el procesamiento en vivo con manejo de errores"""
    global stream
    if stream is None:
        try:
            stream = sd.Stream(
                callback=audio_callback,
                blocksize=block_size,
                samplerate=fs,
                channels=1,
                dtype='float32'
            )
            stream.start()
            btn_live.config(text="Detener Micrófono")
        except Exception as e:
            print(f"Error starting stream: {e}")
            tk.messagebox.showerror("Error", f"No se pudo iniciar el micrófono: {e}")
    else:
        stream.stop()
        stream.close()
        stream = None
        btn_live.config(text="Iniciar Micrófono")

def toggle_test_mode():
    """Activa/desactiva el modo de prueba con actualización de frecuencia"""
    global test_mode
    test_mode = not test_mode
    btn_test.config(text="Salir Modo Prueba" if test_mode else "Modo Prueba")
    slider_test_freq.config(state=tk.NORMAL if test_mode else tk.DISABLED)
    if test_mode:
        update_test_tone()

def update_test_tone():
    """Actualiza la frecuencia del tono de prueba continuamente"""
    global current_test_freq
    if test_mode:
        current_test_freq = slider_test_freq.get()
        lbl_test_freq.config(text=f"Frec. Prueba: {current_test_freq:.0f} Hz")
        root.after(100, update_test_tone)

def plot_filter_response():
    """Grafica la respuesta en frecuencia de los filtros activos"""
    plt.figure(figsize=(12, 6))
    plt.title('Respuesta en Frecuencia de los Filtros Activos')
    plt.xlabel('Frecuencia (Hz)')
    plt.ylabel('Amplitud (dB)')
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.xscale('log')
    plt.xlim(20, 20000)
    plt.ylim(-60, 5)
    
    # Frecuencias para evaluar la respuesta
    freqs = np.logspace(np.log10(20), np.log10(20000), 1000)
    
    if var_lowpass.get():
        w, h = signal.sosfreqz(sos_low, worN=freqs, fs=fs)
        plt.plot(w, 20*np.log10(abs(h)), label=f'Pasa Bajas (4kHz)')
    
    if var_highpass.get():
        w, h = signal.sosfreqz(sos_high, worN=freqs, fs=fs)
        plt.plot(w, 20*np.log10(abs(h)), label=f'Pasa Altas (8kHz)')
    
    if var_bandpass.get():
        w, h = signal.sosfreqz(sos_band, worN=freqs, fs=fs)
        plt.plot(w, 20*np.log10(abs(h)), label=f'Pasa Banda (5k-12kHz)')
    
    if var_bandstop.get():
        w, h = signal.sosfreqz(sos_stop, worN=freqs, fs=fs)
        plt.plot(w, 20*np.log10(abs(h)), label=f'Rechaza Banda (4k-8kHz)')
    
    if var_custom.get():
        w, h = signal.sosfreqz(sos_custom, worN=freqs, fs=fs)
        plt.plot(w, 20*np.log10(abs(h)), label=f'Pasa Bajas ({slider_fc.get():.0f}Hz)')
    
    plt.legend()
    plt.tight_layout()
    plt.show()

# Interfaz gráfica mejorada
root = tk.Tk()
root.title("Ecualizador Digital Avanzado")
root.geometry("700x800")

# Variables de control
var_lowpass = tk.BooleanVar(value=True)
var_highpass = tk.BooleanVar()
var_bandpass = tk.BooleanVar()
var_bandstop = tk.BooleanVar()
var_custom = tk.BooleanVar()

# Configuración de estilo
style = ttk.Style()
style.configure('TFrame', background='#f0f0f0')
style.configure('TLabelFrame', background='#f0f0f0')
style.configure('TButton', font=('Helvetica', 10))
style.configure('Title.TLabel', font=('Helvetica', 12, 'bold'))

# Marco principal
main_frame = ttk.Frame(root, padding=15)
main_frame.pack(fill=tk.BOTH, expand=True)

# Sección de archivos
file_frame = ttk.LabelFrame(main_frame, text="Archivo de Audio", padding=10)
file_frame.pack(fill=tk.X, pady=5)

btn_load = ttk.Button(file_frame, text="Cargar Archivo", command=load_audio_file)
btn_load.pack(side=tk.LEFT, padx=5)

btn_play_file = ttk.Button(file_frame, text="Reproducir Archivo", 
                         command=toggle_file_playback, state=tk.DISABLED)
btn_play_file.pack(side=tk.LEFT, padx=5)

lbl_file = ttk.Label(file_frame, text="Ningún archivo cargado")
lbl_file.pack(side=tk.LEFT, padx=5)

# Sección de procesamiento en vivo
live_frame = ttk.LabelFrame(main_frame, text="Procesamiento en Vivo", padding=10)
live_frame.pack(fill=tk.X, pady=5)

btn_live = ttk.Button(live_frame, text="Iniciar Micrófono", command=toggle_live_processing)
btn_live.pack()

# Sección de pruebas
test_frame = ttk.LabelFrame(main_frame, text="Verificación de Filtros", padding=10)
test_frame.pack(fill=tk.X, pady=5)

btn_test = ttk.Button(test_frame, text="Modo Prueba", command=toggle_test_mode)
btn_test.pack(side=tk.LEFT, padx=5)

slider_test_freq = ttk.Scale(test_frame, from_=20, to=20000, orient="horizontal")
slider_test_freq.set(1000)
slider_test_freq.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
slider_test_freq.config(state=tk.DISABLED)

lbl_test_freq = ttk.Label(test_frame, text="Frec. Prueba: 1000 Hz")
lbl_test_freq.pack(side=tk.LEFT, padx=5)

btn_plot = ttk.Button(test_frame, text="Graficar Filtros", command=plot_filter_response, state=tk.DISABLED)
btn_plot.pack(side=tk.RIGHT, padx=5)

# Controles de filtros
filters_frame = ttk.LabelFrame(main_frame, text="Filtros", padding=10)
filters_frame.pack(fill=tk.BOTH, expand=True, pady=5)

def create_filter_control(parent, text, var, tooltip=None):
    """Crea un control de filtro con checkbox y tooltip"""
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, pady=3)
    
    chk = ttk.Checkbutton(frame, text=text, variable=var)
    chk.pack(side=tk.LEFT)
    
    if tooltip:
        ToolTip(chk, text=tooltip)
    
    return frame

# Tooltip simple para mejor usabilidad
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tip_window, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

# Controles individuales para cada filtro con tooltips
create_filter_control(filters_frame, "Pasa Bajas (<4kHz)", var_lowpass, 
                    "Filtro pasa bajas con frecuencia de corte en 4kHz")
create_filter_control(filters_frame, "Pasa Altas (>8kHz)", var_highpass,
                    "Filtro pasa altas con frecuencia de corte en 8kHz")
create_filter_control(filters_frame, "Pasa Banda (5k-12kHz)", var_bandpass,
                    "Filtro pasa banda entre 5kHz y 12kHz")
create_filter_control(filters_frame, "Rechaza Banda (4k-8kHz)", var_bandstop,
                    "Filtro rechaza banda entre 4kHz y 8kHz")

# Filtro configurable
custom_frame = ttk.Frame(filters_frame)
custom_frame.pack(fill=tk.X, pady=5)

ttk.Checkbutton(custom_frame, text="Pasa Bajas Configurable", variable=var_custom).pack(side=tk.LEFT)
ttk.Label(custom_frame, text="Frecuencia:").pack(side=tk.LEFT, padx=5)
slider_fc = ttk.Scale(custom_frame, from_=100, to=15000, orient="horizontal")
slider_fc.set(fc_custom)
slider_fc.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
lbl_fc = ttk.Label(custom_frame, text=f"{fc_custom} Hz")
lbl_fc.pack(side=tk.LEFT, padx=5)

# Actualización de etiqueta de frecuencia
def update_fc_label(*args):
    lbl_fc.config(text=f"{slider_fc.get():.0f} Hz")
slider_fc.config(command=update_fc_label)

# Barra de estado
status_bar = ttk.Frame(root)
status_bar.pack(fill=tk.X, pady=(5,0))

lbl_status = ttk.Label(status_bar, text="Listo", relief=tk.SUNKEN, anchor=tk.W)
lbl_status.pack(fill=tk.X)

# Manejo de cierre seguro
def on_closing():
    global stream
    if stream is not None:
        stream.stop()
        stream.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()