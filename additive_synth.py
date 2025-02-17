import customtkinter as ctk
import numpy as np
import sounddevice as sd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from threading import Timer
from tkinter import simpledialog, messagebox

from utils import ScrollableFrame
from preset_manager import PresetManager
from tooltips import Tooltip

class AdditiveSynth:
    def __init__(self, parent, sample_rate, duration, preset_manager, user_id):
        self.parent = parent
        self.sample_rate = sample_rate
        self.duration = duration
        self.preset_manager = preset_manager  # Initialize preset_manager
        self.user_id = user_id

        # Initialize variables
        self.update_timer = None  # Initialize update_timer
        self.adsr_sliders = {}
        self.create_ui()

        #Track preset name
        self.loaded_preset_name = None 


    def create_ui(self):
        """Initialize the UI."""
        self.control_frame = ScrollableFrame(self.parent, width=300)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.graph_frame = ctk.CTkFrame(self.parent)
        self.graph_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        # Add sliders
        self.base_freq_slider = self.add_slider(self.control_frame, "Base Frequency (Hz)", 20, 2000, 440)
        self.volume_slider = self.add_slider(self.control_frame, "Volume", 0.0, 1.0, 0.5)
        self.harmonics_slider = self.add_slider(self.control_frame, "Number of Harmonics", 1, 50, 10)
        self.tone_slider = self.add_slider(self.control_frame, "Tone", 0.0, 1.0, 0.5)
        self.rolloff_slider = self.add_slider(self.control_frame, "Harmonic Roll-Off", 0.1, 2.0, 1.0)
        
        Tooltip(self.base_freq_slider,'Chooses the funamental frequency of the sound.')
        Tooltip(self.volume_slider,'Determines the volume of the sound')
        Tooltip(self.harmonics_slider,'Chooses the number of harmonic partials the sound is comprised of.')
        Tooltip(self.tone_slider,'Alters the balance of the odd and even frequencies to create a different timbre')
        Tooltip(self.rolloff_slider,'Alters the rate at which the harmonics decrease in amplitude, can create a more subtle sound')

        # ADSR Controls
        for param in ["Attack", "Decay", "Sustain", "Release"]:
            slider = self.add_slider(
                self.control_frame,
                param,
                0.01,
                1.0 if param != "Sustain" else 1.0,
                0.1 if param in ["Attack", "Decay"] else 0.7
            )
            self.adsr_sliders[param.lower()] = slider

        # Play Button
        self.play_button = ctk.CTkButton(self.control_frame, text="Play Sound", command=self.play_sound)
        self.play_button.pack(pady=10)

        # Save Preset Button
        self.save_button = ctk.CTkButton(self.control_frame, text="Save Preset", command=self.save_current_preset)
        self.save_button.pack(pady=10)

        # Graphs
        self.figure, (self.freq_ax, self.adsr_ax) = plt.subplots(2, 1, figsize=(5, 5))
        self.canvas = FigureCanvasTkAgg(self.figure, self.graph_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill="both")

        # Initial graph updates
        self.update_graphs()

    def add_slider(self, frame, label_text, min_value, max_value, initial_value):
        """Helper function to add a labeled slider."""
        ctk.CTkLabel(frame, text=label_text).pack()
        slider = ctk.CTkSlider(frame, from_=min_value, to=max_value, command=self.debounced_update)
        slider.set(initial_value)
        slider.pack(pady=10)
        return slider
        
    def save_current_preset(self):
        """Save the current settings, checking for overwrite and pre-filling the preset name."""
        # Pre-fill the save dialog with the loaded preset name (if it exists)
        initial_name = self.loaded_preset_name if self.loaded_preset_name else ""

        # Prompt the user for the preset name
        preset_name = simpledialog.askstring("Save Preset", "Enter preset name:", initialvalue=initial_name)
        if not preset_name:
            print("Preset name cannot be empty.")
            return  # User canceled or entered an empty name

        # Check if the preset already exists
        if self.preset_manager.preset_exists(preset_name, "Additive"):
            # Ask the user if they want to overwrite the existing preset
            confirm = messagebox.askyesno("Overwrite Preset", f"A preset named '{preset_name}' already exists. Do you want to overwrite it?")
            if not confirm:
                return  # User canceled the overwrite

        # Get the current settings, including the preset name
        preset_data = self.get_preset_data(preset_name)

        # Save the preset (this will overwrite if it already exists)
        self.preset_manager.save_preset(preset_name, "Additive", preset_data)

    def get_preset_data(self, preset_name):
        """Get the current settings of the additive synthesizer."""
        return {
            "type": "Additive",  # Explicitly include the synth type
            "name": preset_name,  # Dynamic preset name
            "base_frequency": self.base_freq_slider.get(),
            "sample_rate": self.sample_rate,
            "duration": self.duration,
            "volume": self.volume_slider.get(),
            "tone": self.tone_slider.get(),
            "num_harmonics": self.harmonics_slider.get(),
            "adsr": {
                "attack": self.adsr_sliders["attack"].get(),
                "decay": self.adsr_sliders["decay"].get(),
                "sustain": self.adsr_sliders["sustain"].get(),
                "release": self.adsr_sliders["release"].get(),
            },
        }

    def debounced_update(self, *args):
        """Debounce updates for performance."""
        if self.update_timer:
            self.update_timer.cancel()
        self.update_timer = Timer(0.3, self.update_graphs)  # Update after 300 ms
        self.update_timer.start()


    def validate_adsr(self):
        """Ensure ADSR times do not exceed the total duration."""
        total_adsr_time = (
            self.adsr_sliders["attack"].get()
            + self.adsr_sliders["decay"].get()
            + self.adsr_sliders["release"].get()
        )
        if total_adsr_time > self.duration:
            scale_factor = self.duration / total_adsr_time
            for param in ["attack", "decay", "release"]:
                self.adsr_sliders[param].set(self.adsr_sliders[param].get() * scale_factor)

    def update_graphs(self):
        """Redraw waveform and ADSR envelope graphs."""
        self.validate_adsr()

        # Generate waveform
        waveform = self.generate_waveform()

        # FFT for frequency domain
        fft_result = np.fft.rfft(waveform)
        freqs = np.fft.rfftfreq(len(waveform), 1 / self.sample_rate)

        # Update frequency domain graph
        self.freq_ax.clear()
        self.freq_ax.plot(freqs, np.abs(fft_result))
        self.freq_ax.set_title("Frequency Domain")
        self.freq_ax.set_xlabel("Frequency (Hz)")
        self.freq_ax.set_ylabel("Amplitude")

        # ADSR envelope graph
        adsr_env = self.generate_adsr_envelope(len(waveform))
        self.adsr_ax.clear()
        self.adsr_ax.plot(adsr_env)
        self.adsr_ax.set_title("ADSR Envelope")
        self.adsr_ax.set_xlabel("Samples")
        self.adsr_ax.set_ylabel("Amplitude")

        # Redraw the canvas
        self.canvas.draw()

    def generate_waveform(self):
        """Generate the additive waveform based on harmonics and ADSR envelope."""
        t = np.linspace(0, self.duration, int(self.sample_rate * self.duration), endpoint=False)
        waveform = np.zeros_like(t)
        harmonics = int(self.harmonics_slider.get())

        for n in range(1, harmonics + 1):
            amplitude = (1 - self.tone_slider.get()) if n % 2 == 0 else self.tone_slider.get()
            amplitude /= n ** self.rolloff_slider.get()
            waveform += amplitude * np.sin(2 * np.pi * n * self.base_freq_slider.get() * t)

        # Apply volume and ADSR envelope
        waveform *= self.volume_slider.get()
        adsr_env = self.generate_adsr_envelope(len(waveform))
        return waveform * adsr_env

    def generate_adsr_envelope(self, num_samples):
        """Generate an ADSR envelope based on sliders."""
        attack_samples = int(self.adsr_sliders["attack"].get() * self.sample_rate)
        decay_samples = int(self.adsr_sliders["decay"].get() * self.sample_rate)
        sustain_samples = num_samples - attack_samples - decay_samples - int(self.adsr_sliders["release"].get() * self.sample_rate)
        sustain_level = self.adsr_sliders["sustain"].get()

        if sustain_samples < 0:
            sustain_samples = 0

        envelope = np.concatenate([
            np.linspace(0, 1, attack_samples),
            np.linspace(1, sustain_level, decay_samples),
            np.full(sustain_samples, sustain_level),
            np.linspace(sustain_level, 0, num_samples - attack_samples - decay_samples - sustain_samples)
        ])
        return envelope
    
    def load_preset(self, preset_data):
        """Load a preset and update the UI."""
        if not preset_data:
            print("Error: Invalid preset data.")
            return

        # Update the loaded preset name
        self.loaded_preset_name = preset_data.get("name")

        print(f"Loading Additive Preset: {preset_data}")

        # Update UI with the loaded preset data
        self.base_freq_slider.set(preset_data["base_frequency"])
        self.volume_slider.set(preset_data["volume"])
        self.tone_slider.set(preset_data["tone"])
        self.harmonics_slider.set(preset_data["num_harmonics"])

        # Update ADSR sliders
        self.adsr_sliders["attack"].set(preset_data["adsr"]["attack"])
        self.adsr_sliders["decay"].set(preset_data["adsr"]["decay"])
        self.adsr_sliders["sustain"].set(preset_data["adsr"]["sustain"])
        self.adsr_sliders["release"].set(preset_data["adsr"]["release"])

        # Update graphs
        self.update_graphs()



    def play_sound(self):
        """Generate the waveform and play it using SoundDevice."""
        waveform = self.generate_waveform()
        sd.play(waveform, samplerate=self.sample_rate)
