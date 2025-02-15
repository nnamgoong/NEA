# Full Integration of Remaining Features into the UI

import customtkinter as ctk
import wave
import numpy as np
import matplotlib.pyplot as plt
class ADSR:
    def __init__(self, attack, decay, sustain, release, sample_rate):
        """
        Initialize the ADSR envelope generator.

        :param attack: Attack time in seconds.
        :param decay: Decay time in seconds.
        :param sustain: Sustain level (0 to 1).
        :param release: Release time in seconds.
        :param sample_rate: Sampling rate (samples per second).
        """
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.sample_rate = sample_rate

    def generate_envelope(self, duration):
        """
        Generate the ADSR envelope over the specified duration.

        :param duration: Total duration of the sound (seconds).
        :return: Numpy array representing the envelope.
        """
        total_samples = int(duration * self.sample_rate)
        attack_samples = int(self.attack * self.sample_rate)
        decay_samples = int(self.decay * self.sample_rate)
        sustain_samples = max(0, total_samples - attack_samples - decay_samples - int(self.release * self.sample_rate))
        release_samples = total_samples - attack_samples - decay_samples - sustain_samples

        # Generate ADSR segments
        attack_env = np.linspace(0, 1, attack_samples)
        decay_env = np.linspace(1, self.sustain, decay_samples)
        sustain_env = np.full(sustain_samples, self.sustain)
        release_env = np.linspace(self.sustain, 0, release_samples)

        # Combine all segments
        envelope = np.concatenate([attack_env, decay_env, sustain_env, release_env])
        return envelope[:total_samples]

def plot_single_wavelength(waveform, sample_rate, base_frequency):
    wavelength_samples = int(sample_rate / base_frequency)
    t = np.linspace(0, 1 / base_frequency, wavelength_samples, endpoint=False)
    plt.figure(figsize=(8, 4))
    plt.plot(t, waveform[:wavelength_samples], color="purple")
    plt.title("Single Wavelength")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.grid()
    plt.show()

def plot_fft(fft_result, sample_rate):
    n = len(fft_result)
    freqs = np.fft.fftfreq(n, d=1/sample_rate)
    magnitudes = np.abs(fft_result)[:n // 2]
    plt.figure(figsize=(8, 4))
    plt.plot(freqs[:n // 2], magnitudes, color="red")
    plt.title("Frequency Domain (FFT)")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.grid()
    plt.show()


class FFTProcessor:
    @staticmethod
    def bit_reversal(values):
        n = len(values)
        result = [0] * n
        bits = int(np.log2(n))
        for i in range(n):
            reversed_idx = int(bin(i)[2:].zfill(bits)[::-1], 2)
            result[reversed_idx] = values[i]
        return result

    @staticmethod
    def fft(signal):
        n = len(signal)
        if n & (n - 1) != 0:
            raise ValueError("FFT length must be a power of 2.")
        signal = FFTProcessor.bit_reversal(signal)
        step = 2
        while step <= n:
            half_step = step // 2
            twiddle_factor = np.exp(-2j * np.pi * np.arange(half_step) / step)
            for i in range(0, n, step):
                for k in range(half_step):
                    temp = twiddle_factor[k] * signal[i + k + half_step]
                    signal[i + k + half_step] = signal[i + k] - temp
                    signal[i + k] += temp
            step *= 2
        return signal

# Subtractive Synthesis Implementation
class AdditiveSynth:
    def __init__(self, base_frequency, sample_rate, duration, method="partials", num_harmonics=10):
        """
        Initialize the additive synthesizer.

        :param base_frequency: Base frequency for synthesis (Hz).
        :param sample_rate: Sampling rate (samples per second).
        :param duration: Duration of the sound (seconds).
        :param method: "partials" for predefined harmonic sliders, "manual" for user-defined harmonics.
        :param num_harmonics: Number of harmonics to include (for "partials" method).
        """
        self.base_frequency = base_frequency
        self.sample_rate = sample_rate
        self.duration = duration
        self.method = method
        self.num_harmonics = num_harmonics  # Used for "partials" method
        self.harmonics = []  # List of (amplitude, phase) tuples for manual mode

    def generate_waveform(self):
        """
        Generate a waveform based on the chosen method.
        """
        t = np.linspace(0, self.duration, int(self.sample_rate * self.duration), endpoint=False)
        if self.method == "partials":
            return self._partials_slider(t)
        elif self.method == "manual":
            return self._manual_harmonics(t)
        else:
            raise ValueError("Invalid synthesis method. Choose 'partials' or 'manual'.")

    def _partials_slider(self, t):
        """
        Generate waveform with harmonics controlled by a slider.
        """
        waveform = np.zeros_like(t)
        for i in range(1, self.num_harmonics + 1):
            amplitude = 1 / i  # Harmonic amplitude decreases with order
            waveform += amplitude * np.sin(2 * np.pi * self.base_frequency * i * t)
        return waveform

    def _manual_harmonics(self, t):
        """
        Generate waveform with user-defined harmonic amplitudes and phases.
        """
        waveform = np.zeros_like(t)
        for i, (amplitude, phase) in enumerate(self.harmonics, start=1):
            waveform += amplitude * np.sin(2 * np.pi * self.base_frequency * i * t + phase)
        return waveform

    def set_harmonics(self, harmonics):
        """
        Set harmonics for manual mode.

        :param harmonics: List of tuples [(amplitude, phase), ...].
        """
        self.harmonics = harmonics




class SubtractiveSynth:
    def __init__(self, oscillator_type="sine", sample_rate=44100, duration=1.0):
        """
        Initialize the subtractive synthesizer.

        :param oscillator_type: Type of oscillator ("sine", "square", "sawtooth", "triangle").
        :param sample_rate: Sampling rate (samples per second).
        :param duration: Duration of the sound (seconds).
        """
        self.oscillator_type = oscillator_type
        self.sample_rate = sample_rate
        self.duration = duration

    def generate_waveform(self):
        """
        Generate a basic waveform based on the oscillator type.
        """
        t = np.linspace(0, self.duration, int(self.sample_rate * self.duration), endpoint=False)
        if self.oscillator_type == "sine":
            return np.sin(2 * np.pi * 440 * t)  # Default frequency set to 440 Hz (A4)
        elif self.oscillator_type == "square":
            return np.sign(np.sin(2 * np.pi * 440 * t))
        elif self.oscillator_type == "sawtooth":
            return 2 * (t * 440 % 1) - 1
        elif self.oscillator_type == "triangle":
            return 2 * np.abs(2 * (t * 440 % 1) - 1) - 1
        else:
            raise ValueError("Invalid oscillator type. Choose 'sine', 'square', 'sawtooth', or 'triangle'.")

    def apply_low_pass_filter(self, waveform, cutoff_freq):
        """
        Apply a simple low-pass filter to the waveform.

        :param waveform: The input waveform.
        :param cutoff_freq: The cutoff frequency for the low-pass filter (Hz).
        """
        # Design a simple FIR low-pass filter
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        num_taps = 101  # Filter order
        coefficients = np.sinc(2 * normalized_cutoff * (np.arange(num_taps) - (num_taps - 1) / 2))
        coefficients *= np.hamming(num_taps)  # Apply a Hamming window
        coefficients /= np.sum(coefficients)  # Normalize coefficients

        # Apply filter using convolution
        filtered_waveform = np.convolve(waveform, coefficients, mode='same')
        return filtered_waveform



class SincInterpolator:
    @staticmethod
    def sinc_kernel(original_rate, target_rate, kernel_size, window="hamming"):
        """
        Create a sinc interpolation kernel for resampling.

        :param original_rate: Original sample rate of the waveform.
        :param target_rate: Target sample rate for resampling.
        :param kernel_size: Size of the interpolation kernel.
        :param window: Type of window function to apply (e.g., "hamming").
        :return: The sinc interpolation kernel.
        """
        ratio = target_rate / original_rate
        x = np.arange(-kernel_size, kernel_size + 1)
        sinc_func = np.sinc(x / ratio)

        # Apply a window function
        if window == "hamming":
            win = np.hamming(len(x))
        elif window == "blackman":
            win = np.blackman(len(x))
        else:
            raise ValueError("Unsupported window type")

        kernel = sinc_func * win
        return kernel / np.sum(kernel)  # Normalize

    @staticmethod
    def interpolate(samples, original_rate, target_rate):
        """
        Resample a waveform using sinc interpolation.

        :param samples: The input waveform.
        :param original_rate: Original sample rate of the waveform.
        :param target_rate: Target sample rate for resampling.
        :return: Resampled waveform.
        """
        kernel_size = 64  # Larger kernel size = better quality
        kernel = SincInterpolator.sinc_kernel(original_rate, target_rate, kernel_size)
        resampled_signal = np.convolve(samples, kernel, mode="same")

        # Adjust the sample length to fit the new rate
        duration = len(samples) / original_rate
        new_length = int(target_rate * duration)
        return np.interp(
            np.linspace(0, len(samples) - 1, new_length),
            np.arange(len(samples)),
            resampled_signal
        )

class WaveformExporter:
    @staticmethod
    def export_to_wav(waveform, sample_rate, filename="output.wav"):
        """
        Export a waveform to a .wav file.

        :param waveform: The input waveform (numpy array).
        :param sample_rate: The sample rate of the waveform.
        :param filename: Name of the output file.
        """
        # Normalize waveform to 16-bit PCM range
        waveform_int16 = np.int16(waveform / np.max(np.abs(waveform)) * 32767)

        # Write the waveform to a WAV file
        with wave.open(filename, "w") as wav_file:
            wav_file.setnchannels(1)  # Mono audio
            wav_file.setsampwidth(2)  # 16-bit samples
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(waveform_int16.tobytes())


# Revised Implementation Utilizing Core Classes

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
import numpy as np
import customtkinter as ctk


import sounddevice as sd

class SynthApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Synthesis Program")
        self.geometry("1400x900")
        self.resizable(True, True)

        # Parameters
        self.synthesis_mode = "additive"
        self.sample_rate = 44100
        self.duration = 1.0
        self.base_frequency = 440
        self.num_harmonics = 10  # Increased range for partials
        self.tone_factor = 1.0  # Default tone modifier (for tone slider)
        self.attack = 0.1
        self.decay = 0.1
        self.sustain = 0.7
        self.release = 0.2

        # Synthesis Object
        self.synth = AdditiveSynth(base_frequency=self.base_frequency,
                                   sample_rate=self.sample_rate,
                                   duration=self.duration,
                                   method="partials",
                                   num_harmonics=self.num_harmonics)

        # Initialize UI
        self.create_widgets()
        self.update_graphs()  # Ensure graphs are rendered with initial parameters

    def create_widgets(self):
        """
        Create UI components and layout.
        """
        # Title Label
        self.title_label = ctk.CTkLabel(self, text="Synthesis Program", font=("Arial", 24))
        self.title_label.pack(pady=10)

        # Frame for controls
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(pady=20, padx=20, fill="x")

        # Base Frequency Slider
        self.freq_label = ctk.CTkLabel(self.control_frame, text="Base Frequency (Hz):")
        self.freq_label.grid(row=0, column=0, padx=5, pady=5)
        self.freq_slider = ctk.CTkSlider(self.control_frame, from_=20, to=2000, number_of_steps=1980)
        self.freq_slider.grid(row=0, column=1, padx=5, pady=5)
        self.freq_slider.set(self.base_frequency)
        self.freq_slider.bind("<ButtonRelease-1>", self.update_synthesis_parameters)

        # Duration Slider
        self.duration_label = ctk.CTkLabel(self.control_frame, text="Duration (s):")
        self.duration_label.grid(row=1, column=0, padx=5, pady=5)
        self.duration_slider = ctk.CTkSlider(self.control_frame, from_=0.1, to=5, number_of_steps=49)
        self.duration_slider.grid(row=1, column=1, padx=5, pady=5)
        self.duration_slider.set(self.duration)
        self.duration_slider.bind("<ButtonRelease-1>", self.update_synthesis_parameters)

        # Partials Slider with Label
        self.partials_label = ctk.CTkLabel(self.control_frame, text="Number of Harmonics:")
        self.partials_label.grid(row=2, column=0, padx=5, pady=5)
        self.partials_slider = ctk.CTkSlider(self.control_frame, from_=1, to=100, number_of_steps=99)
        self.partials_slider.grid(row=2, column=1, padx=5, pady=5)
        self.partials_slider.set(self.num_harmonics)
        self.partials_slider.bind("<ButtonRelease-1>", self.update_synthesis_parameters)

        self.partials_value_label = ctk.CTkLabel(self.control_frame, text=f"{self.num_harmonics} harmonics")
        self.partials_value_label.grid(row=2, column=2, padx=5, pady=5)

        # Tone Slider
        self.tone_label = ctk.CTkLabel(self.control_frame, text="Tone:")
        self.tone_label.grid(row=3, column=0, padx=5, pady=5)
        self.tone_slider = ctk.CTkSlider(self.control_frame, from_=0.5, to=2.0, number_of_steps=30)
        self.tone_slider.grid(row=3, column=1, padx=5, pady=5)
        self.tone_slider.set(self.tone_factor)
        self.tone_slider.bind("<ButtonRelease-1>", self.update_synthesis_parameters)

        # ADSR Sliders
        self.adsr_frame = ctk.CTkFrame(self)
        self.adsr_frame.pack(pady=10, padx=20, fill="x")
        
        self.attack_label = ctk.CTkLabel(self.adsr_frame, text="Attack (s):")
        self.attack_label.grid(row=0, column=0, padx=5, pady=5)
        self.attack_slider = ctk.CTkSlider(self.adsr_frame, from_=0, to=1, number_of_steps=100)
        self.attack_slider.grid(row=0, column=1, padx=5, pady=5)
        self.attack_slider.set(self.attack)
        self.attack_slider.bind("<ButtonRelease-1>", self.update_adsr_parameters)

        self.decay_label = ctk.CTkLabel(self.adsr_frame, text="Decay (s):")
        self.decay_label.grid(row=1, column=0, padx=5, pady=5)
        self.decay_slider = ctk.CTkSlider(self.adsr_frame, from_=0, to=1, number_of_steps=100)
        self.decay_slider.grid(row=1, column=1, padx=5, pady=5)
        self.decay_slider.set(self.decay)
        self.decay_slider.bind("<ButtonRelease-1>", self.update_adsr_parameters)

        self.sustain_label = ctk.CTkLabel(self.adsr_frame, text="Sustain (level):")
        self.sustain_label.grid(row=2, column=0, padx=5, pady=5)
        self.sustain_slider = ctk.CTkSlider(self.adsr_frame, from_=0, to=1, number_of_steps=100)
        self.sustain_slider.grid(row=2, column=1, padx=5, pady=5)
        self.sustain_slider.set(self.sustain)
        self.sustain_slider.bind("<ButtonRelease-1>", self.update_adsr_parameters)

        self.release_label = ctk.CTkLabel(self.adsr_frame, text="Release (s):")
        self.release_label.grid(row=3, column=0, padx=5, pady=5)
        self.release_slider = ctk.CTkSlider(self.adsr_frame, from_=0, to=1, number_of_steps=100)
        self.release_slider.grid(row=3, column=1, padx=5, pady=5)
        self.release_slider.set(self.release)
        self.release_slider.bind("<ButtonRelease-1>", self.update_adsr_parameters)

        # Play Sound Button
        self.play_button = ctk.CTkButton(self, text="Play Sound", command=self.play_sound)
        self.play_button.pack(pady=20)

        # Always-On Graphs
        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Matplotlib Figures
        self.fig, (self.ax_time, self.ax_freq) = plt.subplots(2, 1, figsize=(10, 6))
        self.fig.tight_layout(pad=3.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def update_synthesis_parameters(self, event=None):
        """
        Update synthesis parameters based on UI inputs.
        """
        self.base_frequency = self.freq_slider.get()
        self.duration = self.duration_slider.get()
        self.num_harmonics = int(self.partials_slider.get())
        self.tone_factor = self.tone_slider.get()

        self.partials_value_label.configure(text=f"{self.num_harmonics} harmonics")  # Update label

        # Update the AdditiveSynth instance
        self.synth = AdditiveSynth(base_frequency=self.base_frequency,
                                   sample_rate=self.sample_rate,
                                   duration=self.duration,
                                   method="partials",
                                   num_harmonics=self.num_harmonics)

        # Update the graphs
        self.update_graphs()

    def update_adsr_parameters(self, event=None):
        """
        Update ADSR envelope parameters and validate against duration.
        """
        self.attack = self.attack_slider.get()
        self.decay = self.decay_slider.get()
        self.sustain = self.sustain_slider.get()
        self.release = self.release_slider.get()

        # Validation to ensure ADSR parameters fit within the duration
        total_adsr_time = self.attack + self.decay + self.release
        if total_adsr_time > self.duration:
            excess = total_adsr_time - self.duration
            if self.release > excess:
                self.release -= excess
            elif self.decay > excess:
                self.decay -= excess
            else:
                self.attack -= excess

            # Update sliders to reflect adjustments
            self.attack_slider.set(self.attack)
            self.decay_slider.set(self.decay)
            self.release_slider.set(self.release)

        self.update_graphs()

    def play_sound(self):
        """
        Play the synthesized sound.
        """
        waveform = self.synth.generate_waveform()
        envelope = ADSR(self.attack, self.decay, self.sustain, self.release, self.sample_rate).generate_envelope(self.duration)
        shaped_waveform = waveform * envelope
        sd.play(shaped_waveform, samplerate=self.sample_rate)

    def update_graphs(self):
        """
        Update the time-domain and frequency-domain graphs.
        """
        # Generate waveform with tone adjustment
        waveform = self.synth.generate_waveform()
        harmonic_weights = np.linspace(1.0, self.tone_factor, self.num_harmonics)
        waveform *= np.dot(harmonic_weights, waveform[:self.num_harmonics])

        # Apply ADSR envelope
        envelope = ADSR(self.attack, self.decay, self.sustain, self.release, self.sample_rate).generate_envelope(self.duration)
        shaped_waveform = waveform * envelope

        # Time-Domain Graph
        wavelength_samples = int(self.sample_rate / self.base_frequency)
        t_wavelength = np.linspace(0, 1 / self.base_frequency, wavelength_samples, endpoint=False)
        self.ax_time.clear()
        self.ax_time.plot(t_wavelength, shaped_waveform[:wavelength_samples], color="purple")
        self.ax_time.set_title("Time Domain (Single Wavelength)")
        self.ax_time.set_xlabel("Time (s)")
        self.ax_time.set_ylabel("Amplitude")

        # Frequency-Domain Graph
        fft_result = np.fft.fft(shaped_waveform)
        n = len(fft_result)
        freqs = np.fft.fftfreq(n, d=1 / self.sample_rate)
        magnitudes = np.abs(fft_result)[:n // 2]
        self.ax_freq.clear()
        self.ax_freq.plot(freqs[:n // 2], magnitudes, color="red")
        self.ax_freq.set_title("Frequency Domain (FFT)")
        self.ax_freq.set_xlabel("Frequency (Hz)")
        self.ax_freq.set_ylabel("Amplitude")

        # Update canvas
        self.canvas.draw()


# Instantiate and run the application\
if __name__ == "__main__":
    app = SynthApp()
    app.mainloop()
