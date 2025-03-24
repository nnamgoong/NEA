import customtkinter as ctk
import numpy as np
import sounddevice as sd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from threading import Timer
from tkinter import simpledialog, messagebox
import threading

from utils import ScrollableFrame, FFT
from preset_manager import PresetManager
from tooltips import Tooltip

class AdditiveSynth:
    def __init__(self, parent, sample_rate, duration, preset_manager, user_id):
        self.parent = parent
        self.sample_rate = sample_rate
        self.duration = duration
        self.preset_manager = preset_manager
        self.user_id = user_id

        # Initialize variables
        self.update_timer = None
        self.adsr_sliders = {}
        self.create_ui()

        # Track preset name
        self.loaded_preset_name = None

    def create_ui(self):
        """Initialize the UI."""
        # Main Layout: Controls on the left, Graphs on the right
        self.controls_frame = ctk.CTkFrame(self.parent, width=300)
        self.controls_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.graph_frame = ctk.CTkFrame(self.parent)
        self.graph_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        # Scrollable area for sliders
        self.scrollable_frame = ScrollableFrame(self.controls_frame, width=450)
        self.scrollable_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Add duration input
        self.duration_label = ctk.CTkLabel(self.scrollable_frame, text="Duration (seconds)")
        self.duration_label.pack(pady=(10, 0))
        self.duration_entry = ctk.CTkEntry(self.scrollable_frame)
        self.duration_entry.insert(0, str(self.duration))  # Set default duration
        self.duration_entry.pack(pady=5)
        Tooltip(self.duration_entry, "Set the duration of the sound in seconds.")

        # Replace frequency slider with an input box
        self.base_freq_label = ctk.CTkLabel(self.scrollable_frame, text="Base Frequency (Hz)")
        self.base_freq_label.pack(pady=(10, 0))
        self.base_freq_entry = ctk.CTkEntry(self.scrollable_frame)
        self.base_freq_entry.insert(0, "440")  # Default frequency (A4)
        self.base_freq_entry.pack(pady=5)
        Tooltip(self.base_freq_entry, "Set the fundamental frequency of the sound.")

        # Add volume slider
        self.volume_slider = self.add_slider(self.scrollable_frame, "Volume", 0.0, 1.0, 0.5)
        Tooltip(self.volume_slider, "Determines the volume of the sound.")

        # Add harmonics slider with a label to display the current value
        self.harmonics_frame = ctk.CTkFrame(self.scrollable_frame)
        self.harmonics_frame.pack(pady=(10, 0))
        self.harmonics_label = ctk.CTkLabel(self.harmonics_frame, text="Number of Harmonics")
        self.harmonics_label.pack(side="left", padx=5)
        self.harmonics_value_label = ctk.CTkLabel(self.harmonics_frame, text="10")  # Default value
        self.harmonics_value_label.pack(side="right", padx=5)
        self.harmonics_slider = ctk.CTkSlider(
            self.scrollable_frame, from_=1, to=50, command=self.debounced_update
        )
        self.harmonics_slider.set(10)  # Default value
        self.harmonics_slider.pack(pady=5)
        Tooltip(self.harmonics_slider, "Chooses the number of harmonic partials the sound is comprised of.")

        # Add tone slider
        self.tone_slider = self.add_slider(self.scrollable_frame, "Tone", 0.0, 1.0, 0.5)
        Tooltip(self.tone_slider, "Alters the balance of the odd and even frequencies to create a different timbre.")

        # Add rolloff slider
        self.rolloff_slider = self.add_slider(self.scrollable_frame, "Harmonic Roll-Off", 0.1, 2.0, 1.0)
        Tooltip(self.rolloff_slider, "Alters the rate at which the harmonics decrease in amplitude, can create a more subtle sound.")

        """Initialize the UI."""
        # ADSR Controls
        for param in ["Attack", "Decay", "Sustain", "Release"]:
            slider = self.add_slider(
                self.scrollable_frame,
                param,
                0.01,
                1.0 if param != "Sustain" else 1.0,
                0.1 if param in ["Attack", "Decay"] else 0.7
            )
            self.adsr_sliders[param.lower()] = slider

            # Add tooltips for ADSR sliders
            if param == "Attack":
                Tooltip(slider, "Set the attack time (how quickly the sound reaches full volume).")
            elif param == "Decay":
                Tooltip(slider, "Set the decay time (how quickly the sound drops to the sustain level).")
            elif param == "Sustain":
                Tooltip(slider, "Set the sustain level (the volume during the sustain phase).")
            elif param == "Release":
                Tooltip(slider, "Set the release time (how quickly the sound fades out after releasing a note).")
                
        # Play Button (outside the scrollable frame)
        self.play_button = ctk.CTkButton(self.controls_frame, text="Play Sound", command=self.play_sound)
        self.play_button.pack(side="bottom", pady=10)

        # Save Preset Button (outside the scrollable frame)
        self.save_button = ctk.CTkButton(self.controls_frame, text="Save Preset", command=self.save_current_preset)
        self.save_button.pack(side="bottom", pady=10)

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
            "base_frequency": float(self.base_freq_entry.get()),  # Get frequency from entry box
            "sample_rate": self.sample_rate,
            "duration": float(self.duration_entry.get()),  # Get duration from entry box
            "volume": self.volume_slider.get(),
            "tone": self.tone_slider.get(),
            "num_harmonics": int(self.harmonics_slider.get()),
            "adsr": {
                "attack": self.adsr_sliders["attack"].get(),
                "decay": self.adsr_sliders["decay"].get(),
                "sustain": self.adsr_sliders["sustain"].get(),
                "release": self.adsr_sliders["release"].get(),
            },
        }

    def debounced_update(self, *args):
        """Faster debounced updates for graphs"""
        # Cancel any pending updates
        if hasattr(self, '_update_timer'):
            self.after_cancel(self._update_timer)
        
        # Schedule update after shorter delay (100ms instead of 300ms)
        self._update_timer = self.after(100, self.update_graphs)

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
        fft_result = FFT.rfft(waveform) / len(waveform)  # Normalize the FFT output
        freqs = FFT.rfftfreq(len(waveform), 1 / self.sample_rate)

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

    def generate_waveform(self) -> np.ndarray:
        """
        Generate the additive waveform using IFFT and adjust for duration.
        """
        # Get the number of harmonics
        num_harmonics = int(self.harmonics_slider.get())

        # Get the base frequency from the entry box
        base_freq = float(self.base_freq_entry.get())

        # Create the frequency domain representation
        freqs = np.arange(1, num_harmonics + 1) * base_freq
        amplitudes = 1 / (np.arange(1, num_harmonics + 1)) ** self.rolloff_slider.get()

        # Apply tone control (balance odd and even harmonics)
        tone_value = self.tone_slider.get()

        # Enhanced tone control: Apply a nonlinear scaling factor
        if tone_value < 0.5:
            # Reduce even harmonics more aggressively
            even_reduction = 1 - (tone_value * 2)  # Scale from 1 to 0 as tone_value goes from 0 to 0.5
            amplitudes[::2] *= even_reduction ** 2  # Square the reduction for a more pronounced effect
        else:
            # Reduce odd harmonics more aggressively
            odd_reduction = (tone_value - 0.5) * 2  # Scale from 0 to 1 as tone_value goes from 0.5 to 1
            amplitudes[1::2] *= odd_reduction ** 2  # Square the reduction for a more pronounced effect

        # Create the frequency domain array
        N = int(self.sample_rate * self.duration)  # Use the default duration for FFT
        freq_domain = np.zeros(N // 2 + 1, dtype=complex)

        # Place the harmonics in the frequency domain
        for freq, amp in zip(freqs, amplitudes):
            bin_index = int(freq * N / self.sample_rate)
            if bin_index < len(freq_domain):
                freq_domain[bin_index] = amp

        # Perform the IFFT to generate the time-domain waveform
        waveform = FFT.irfft(freq_domain)

        # Normalize the waveform
        waveform /= np.max(np.abs(waveform))

        # Apply volume
        waveform *= self.volume_slider.get()

        # Adjust the waveform to match the desired duration
        desired_samples = int(self.sample_rate * float(self.duration_entry.get()))
        if len(waveform) < desired_samples:
            # Repeat the waveform if it's shorter than the desired duration
            waveform = np.tile(waveform, int(np.ceil(desired_samples / len(waveform))))
        waveform = waveform[:desired_samples]  # Truncate to the desired duration

        # Generate the ADSR envelope for the entire desired duration
        adsr_env = self.generate_adsr_envelope(len(waveform))

        # Apply the ADSR envelope to the waveform
        waveform *= adsr_env

        return waveform

    def generate_adsr_envelope(self, num_samples: int) -> np.ndarray:
        """
        Generate an ADSR envelope based on sliders for the entire duration.
        """
        attack_samples = int(self.adsr_sliders["attack"].get() * self.sample_rate)
        decay_samples = int(self.adsr_sliders["decay"].get() * self.sample_rate)
        sustain_samples = num_samples - attack_samples - decay_samples - int(
            self.adsr_sliders["release"].get() * self.sample_rate
        )
        sustain_level = self.adsr_sliders["sustain"].get()

        if sustain_samples < 0:
            # If the total ADSR time exceeds the duration, scale the times
            total_adsr_time = attack_samples + decay_samples + int(
                self.adsr_sliders["release"].get() * self.sample_rate
            )
            scale_factor = num_samples / total_adsr_time
            attack_samples = int(attack_samples * scale_factor)
            decay_samples = int(decay_samples * scale_factor)
            sustain_samples = 0

        envelope = np.concatenate([
            np.linspace(0, 1, attack_samples),  # Attack
            np.linspace(1, sustain_level, decay_samples),  # Decay
            np.full(sustain_samples, sustain_level),  # Sustain
            np.linspace(sustain_level, 0, num_samples - attack_samples - decay_samples - sustain_samples)  # Release
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
        self.base_freq_entry.delete(0, "end")
        self.base_freq_entry.insert(0, str(preset_data["base_frequency"]))
        self.duration_entry.delete(0, "end")
        self.duration_entry.insert(0, str(preset_data["duration"]))
        self.volume_slider.set(preset_data["volume"])
        self.tone_slider.set(preset_data["tone"])
        self.harmonics_slider.set(preset_data["num_harmonics"])
        self.harmonics_value_label.configure(text=str(int(preset_data["num_harmonics"])))

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
        threading.Thread(target=lambda: sd.play(waveform, samplerate=self.sample_rate),daemon=True).start()