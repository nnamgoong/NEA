import customtkinter as ctk
import numpy as np
import sounddevice as sd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, sosfilt
from threading import Timer
from tkinter import simpledialog, messagebox

from tooltips import Tooltip
from utils import ScrollableFrame



class SubtractiveSynth:
    def __init__(self, parent, sample_rate, duration, update_presets_callback, user_id, preset_manager):
        self.parent = parent
        self.sample_rate = sample_rate
        self.duration = duration
        self.update_presets_callback = update_presets_callback
        self.user_id = user_id
        self.preset_manager = preset_manager 


        # Parameters
        self.effects = []  
        self.oscillators = []
        self.filters = []
        self.lfos = [] 

        self.volume = 0.5

        #Track preset name
        self.loaded_preset_name = None 

        # Timer for debounced updates
        self.update_timer = None

        # Initialize the UI
        self.create_ui()

    def create_ui(self):
        """Create the user interface for the synthesizer."""
        # Main Layout: Controls on the left, Graphs on the right
        self.controls_frame = ctk.CTkFrame(self.parent, width=700)  # Increased width
        self.controls_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.graph_frame = ctk.CTkFrame(self.parent)
        self.graph_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_columnconfigure(1, weight=2)
        self.parent.grid_rowconfigure(0, weight=1)

        # Scrollable area for oscillators and filters
        self.scrollable_frame = ScrollableFrame(self.controls_frame, width=450)  # Match width to controls_frame
        self.scrollable_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Add duration input
        self.duration_label = ctk.CTkLabel(self.scrollable_frame, text="Duration (seconds)")
        self.duration_label.pack(pady=(10, 0))
        self.duration_entry = ctk.CTkEntry(self.scrollable_frame)
        self.duration_entry.insert(0, str(self.duration))  # Set default duration
        self.duration_entry.pack(pady=5)
        Tooltip(self.duration_entry, "Set the duration of the sound in seconds.")

        # Volume Slider with Label
        volume_frame = ctk.CTkFrame(self.scrollable_frame)
        volume_frame.pack(pady=10, fill="x")
        ctk.CTkLabel(volume_frame, text="Volume").pack(side="left", padx=5)
        self.volume_slider = ctk.CTkSlider(
            volume_frame, from_=0.0, to=1.0, command=self.debounced_update
        )
        self.volume_slider.set(self.volume)
        self.volume_slider.pack(side="right", fill="x", expand=True)
        Tooltip(self.volume_slider, "Adjust the overall volume of the sound.")

        # Oscillator Controls
        ctk.CTkLabel(self.scrollable_frame, text="Oscillators", font=("Arial", 16)).pack(pady=5)
        self.oscillators_frame = ctk.CTkFrame(self.scrollable_frame)
        self.oscillators_frame.pack(fill="both", expand=True)
        self.add_oscillator_button = ctk.CTkButton(
            self.scrollable_frame, text="Add Oscillator", command=self.add_oscillator
        )
        self.add_oscillator_button.pack(pady=10)

        # Filter Controls
        ctk.CTkLabel(self.scrollable_frame, text="Filters", font=("Arial", 16)).pack(pady=5)
        self.filters_frame = ctk.CTkFrame(self.scrollable_frame)
        self.filters_frame.pack(fill="both", expand=True)
        self.add_filter_button = ctk.CTkButton(
            self.scrollable_frame, text="Add Filter", command=self.add_filter
        )
        self.add_filter_button.pack(pady=10)


        # Static Play Button
        self.play_button = ctk.CTkButton(
            self.controls_frame, text="Play Sound", command=self.play_sound
        )
        self.play_button.pack(side="bottom", pady=10)

        # Graph Areas
        self.figure, (self.wave_ax, self.filter_ax) = plt.subplots(2, 1, figsize=(8, 5))
        self.canvas = FigureCanvasTkAgg(self.figure, self.graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Effects Controls
        ctk.CTkLabel(self.scrollable_frame, text="Effects", font=("Arial", 16)).pack(pady=5)
        self.effects_frame = ctk.CTkFrame(self.scrollable_frame)
        self.effects_frame.pack(pady=10, fill="both", expand=True)
        self.add_effect_button = ctk.CTkButton(
            self.scrollable_frame, text="Add Effect", command=self.add_effect
        )
        self.add_effect_button.pack(pady=10)

        # LFO Controls
        ctk.CTkLabel(self.scrollable_frame, text="LFOs", font=("Arial", 16)).pack(pady=5)
        self.lfos_frame = ctk.CTkFrame(self.scrollable_frame)
        self.lfos_frame.pack(pady=10, fill="both", expand=True)
        self.add_lfo_button = ctk.CTkButton(
            self.scrollable_frame, text="Add LFO", command=self.add_lfo
        )
        self.add_lfo_button.pack(pady=10)

        # Save Preset Button
        self.save_preset_button = ctk.CTkButton(self.controls_frame, text="Save Preset", command=self.save_current_preset)
        self.save_preset_button.pack(pady=10)

        # Initial Graph Update
        self.update_graphs()

    def add_oscillator(self, osc_type="Sine", frequency=440.0, amplitude=0.5):
        """Add a new oscillator with optional preset values."""
        osc_frame = ctk.CTkFrame(self.oscillators_frame)
        osc_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(osc_frame, text="Type").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        type_menu = ctk.CTkComboBox(
            osc_frame, values=["Sine", "Square", "Triangle", "Sawtooth"],
            command=lambda _: self.debounced_update()
        )
        type_menu.set(osc_type)
        type_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(type_menu, "Select the waveform type for this oscillator.")

        ctk.CTkLabel(osc_frame, text="Frequency (Hz)").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        freq_entry = ctk.CTkEntry(osc_frame, width=80)
        freq_entry.insert(0, str(frequency))
        freq_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(freq_entry, "Set the frequency of this oscillator.")

        ctk.CTkLabel(osc_frame, text="Amplitude").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        amp_slider = ctk.CTkSlider(osc_frame, from_=0.0, to=1.0, command=lambda _: self.debounced_update())
        amp_slider.set(amplitude)
        amp_slider.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(amp_slider, "Set the amplitude (volume) of this oscillator.")

        remove_button = ctk.CTkButton(osc_frame, text="Remove", command=lambda: self.remove_oscillator(osc_frame))
        remove_button.grid(row=3, column=0, columnspan=2, pady=5)
        Tooltip(remove_button, "Remove this oscillator.")

        self.oscillators.append({
            "frame": osc_frame,
            "type": type_menu,
            "frequency": freq_entry,
            "amplitude": amp_slider,
        })
        self.debounced_update()



    def remove_oscillator(self, osc_frame):
        """Remove an oscillator from the controls."""
        for osc in self.oscillators:
            if osc["frame"] == osc_frame:
                self.oscillators.remove(osc)
                break
        osc_frame.destroy()
        self.debounced_update()

    def add_filter(self, filter_type="Low-pass", cutoff=1000.0, resonance=1.0):
        """Add a new filter with optional preset values."""
        filter_frame = ctk.CTkFrame(self.filters_frame)
        filter_frame.pack(fill="x", pady=5)

        # Filter type dropdown with tooltip
        ctk.CTkLabel(filter_frame, text="Type").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        type_menu = ctk.CTkComboBox(
            filter_frame, values=["Low-pass", "High-pass", "Band-pass", "Band-reject"],
            command=lambda value: self.update_filter_ui(value, filter_frame)
        )
        type_menu.set(filter_type)
        type_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Add tooltip for the filter type combobox
        self.filter_type_tooltip = Tooltip(type_menu, "Select the type of filter to apply.")

        # Cutoff frequency slider with tooltip
        ctk.CTkLabel(filter_frame, text="Cutoff Frequency (Hz)").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        freq_slider = ctk.CTkSlider(filter_frame, from_=20, to=10000, command=lambda _: self.debounced_update())
        freq_slider.set(cutoff)
        freq_slider.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(freq_slider, "Set the cutoff frequency of the filter.")

        # Resonance slider with tooltip
        ctk.CTkLabel(filter_frame, text="Resonance").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        res_slider = ctk.CTkSlider(filter_frame, from_=0.1, to=10, command=lambda _: self.debounced_update())
        res_slider.set(resonance)
        res_slider.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(res_slider, "Set the resonance (emphasis) of the filter.")

        # Remove button with tooltip
        remove_button = ctk.CTkButton(filter_frame, text="Remove", command=lambda: self.remove_filter(filter_frame))
        remove_button.grid(row=3, column=0, columnspan=2, pady=5)
        Tooltip(remove_button, "Remove this filter.")

        self.filters.append({
            "frame": filter_frame,
            "type": type_menu,
            "frequency": freq_slider,
            "resonance": res_slider,
        })
        self.debounced_update()

        # Update filter UI for the initial filter type
        self.update_filter_ui(filter_type, filter_frame)


    def remove_filter(self, filter_frame):
        """Remove a filter from the controls."""
        for filt in self.filters:
            if filt["frame"] == filter_frame:
                self.filters.remove(filt)
                break
        filter_frame.destroy()
        self.debounced_update()


    def add_effect(self, effect_type="Bitcrusher", params=None):
        """Add a new effect with optional preset values."""
        effect_frame = ctk.CTkFrame(self.effects_frame)
        effect_frame.pack(fill="x", pady=5)

        # Effect type dropdown with tooltip
        ctk.CTkLabel(effect_frame, text="Type").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        type_menu = ctk.CTkComboBox(
            effect_frame,
            values=["Bitcrusher", "Ring Modulation", "Phaser", "Flanger", "Wavefolder", "Chorus"],
            command=lambda value: self.update_effect_ui(value, params_frame, params or {}, type_menu)
        )
        type_menu.set(effect_type)
        type_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Add tooltip for the effect type combobox
        self.effect_type_tooltip = Tooltip(type_menu, "Select the type of effect to apply.")

        params_frame = ctk.CTkFrame(effect_frame)
        params_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        remove_button = ctk.CTkButton(effect_frame, text="Remove", command=lambda: self.remove_effect(effect_frame))
        remove_button.grid(row=2, column=0, columnspan=2, pady=5)
        Tooltip(remove_button, "Remove this effect.")

        # Initialize params as an empty dictionary if it is None
        if params is None:
            params = {}

        self.effects.append({
            "frame": effect_frame,
            "type": type_menu,
            "params": params,
        })

        # Update effect UI for the initial effect type
        self.update_effect_ui(effect_type, params_frame, params, type_menu)

    def update_effect_ui(self, effect_type, params_frame, params, type_menu):
        """Update the effect UI, including tooltips, based on the selected effect type."""
        # Update the tooltip for the effect type combobox
        effect_type_tooltips = {
            "Bitcrusher": "Reduces the bit depth and sample rate of the audio, creating a lo-fi effect.",
            "Ring Modulation": "Multiplies the audio signal with a sine wave, creating metallic or bell-like tones.",
            "Phaser": "Creates a sweeping, swirling effect by modulating phase shifts across frequencies.",
            "Flanger": "Creates a jet-like whooshing effect by mixing the signal with a delayed, modulated copy.",
            "Wavefolder": "Folds the waveform back onto itself, creating harmonic distortion.",
            "Chorus": "Simulates multiple voices by layering detuned copies of the signal."
        }
        if hasattr(self, "effect_type_tooltip"):
            self.effect_type_tooltip.update_text(effect_type_tooltips.get(effect_type, "Select the type of effect to apply."))

        # Clear existing UI elements
        for widget in params_frame.winfo_children():
            widget.destroy()

        # Ensure params is a dictionary
        if params is None:
            params = {}

        # Reset the params dictionary to avoid carrying over old values
        params.clear()

        # Effect parameter definitions
        effect_parameters = {
            "Bitcrusher": [
                ("Bit Depth", "bit_depth", 1, 16, 1, "Reduces the bit depth of the audio, creating a lo-fi effect."),
                ("Sample Rate Reduction", "sample_rate_reduction", 1, 16, 1, "Reduces the sample rate of the audio, creating a gritty effect."),
            ],
            "Ring Modulation": [
                ("Modulation Frequency (Hz)", "mod_freq", 20, 2000, 1, "Set the frequency of the ring modulation effect."),
            ],
            "Phaser": [
                ("Number of Stages", "num_stages", 1, 8, 1, "Set the number of stages in the phaser effect."),
                ("Sweep Frequency (Hz)", "sweep_freq", 0.1, 5.0, 0.1, "Set the frequency of the phaser sweep."),
                ("Depth", "depth", 0.0, 1.0, 0.1, "Set the depth of the phaser effect."),
            ],
            "Flanger": [
                ("Max Delay (ms)", "max_delay", 1, 20, 1, "Set the maximum delay time for the flanger effect."),
                ("Rate (Hz)", "rate", 0.1, 2.0, 0.1, "Set the rate of the flanger modulation."),
            ],
            "Wavefolder": [
                ("Threshold", "threshold", 0.1, 1.0, 0.1, "Set the threshold for wavefolding distortion."),
            ],
            "Chorus": [
                ("Detune Amount", "detune", 0.01, 0.1, 0.01, "Set the amount of detuning for the chorus effect."),
                ("Delay (ms)", "delay", 1, 20, 1, "Set the delay time for the chorus effect."),
                ("Voices", "voices", 2, 8, 1, "Set the number of voices for the chorus effect."),
            ]
        }

        if effect_type not in effect_parameters:
            print(f"Warning: No UI defined for effect type '{effect_type}'")
            return

        # Add sliders for each parameter
        for row, (label, param_key, min_val, max_val, step, tooltip_text) in enumerate(effect_parameters[effect_type]):
            # Add label for the parameter
            ctk.CTkLabel(params_frame, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="w")

            # Add slider for the parameter
            slider = ctk.CTkSlider(
                params_frame,
                from_=min_val,
                to=max_val,
                number_of_steps=int((max_val - min_val) / step)
            )
            slider.set(params.get(param_key, min_val))  # Set to stored value or default
            slider.grid(row=row, column=1, padx=5, pady=5, sticky="ew")

            # Add tooltip for the slider
            Tooltip(slider, tooltip_text)

            # Update params directly when slider changes
            slider.configure(command=lambda _, key=param_key, s=slider: params.update({key: s.get()}))

            # Store the initial value
            params[param_key] = slider.get()

        params_frame.update_idletasks()
                


    def update_filter_ui(self, filter_type, filter_frame):
        """Update the filter UI, including tooltips, based on the selected filter type."""
        # Update the tooltip for the filter type combobox
        filter_type_tooltips = {
            "Low-pass": "Allows frequencies below the cutoff to pass, attenuating higher frequencies.",
            "High-pass": "Allows frequencies above the cutoff to pass, attenuating lower frequencies.",
            "Band-pass": "Allows frequencies within a specific range to pass, attenuating others.",
            "Band-reject": "Attenuates frequencies within a specific range, allowing others to pass."
        }
        if hasattr(self, "filter_type_tooltip"):
            self.filter_type_tooltip.update_text(filter_type_tooltips.get(filter_type, "Select the type of filter to apply."))

        # Update tooltips for frequency and resonance sliders
        filter_tooltips = {
            "Low-pass": {
                "frequency": "Set the cutoff frequency for the low-pass filter (allows frequencies below this value).",
                "resonance": "Set the resonance (emphasis) for the low-pass filter."
            },
            "High-pass": {
                "frequency": "Set the cutoff frequency for the high-pass filter (allows frequencies above this value).",
                "resonance": "Set the resonance (emphasis) for the high-pass filter."
            },
            "Band-pass": {
                "frequency": "Set the center frequency for the band-pass filter (allows frequencies around this value).",
                "resonance": "Set the resonance (emphasis) for the band-pass filter."
            },
            "Band-reject": {
                "frequency": "Set the center frequency for the band-reject filter (attenuates frequencies around this value).",
                "resonance": "Set the resonance (emphasis) for the band-reject filter."
            }
        }

        # Update tooltips for frequency and resonance sliders
        for widget in filter_frame.winfo_children():
            if isinstance(widget, ctk.CTkSlider):
                if "Frequency" in str(widget):
                    Tooltip(widget, filter_tooltips[filter_type]["frequency"])
                elif "Resonance" in str(widget):
                    Tooltip(widget, filter_tooltips[filter_type]["resonance"])



    def add_lfo(self, shape="Sine", frequency=1.0, depth=0.5, target="Frequency"):
        """Add a new LFO with optional preset values."""
        lfo_frame = ctk.CTkFrame(self.lfos_frame)
        lfo_frame.pack(fill="x", pady=5)

        # LFO shape dropdown with tooltip
        ctk.CTkLabel(lfo_frame, text="Shape").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        shape_menu = ctk.CTkComboBox(
            lfo_frame, values=["Sine", "Square", "Triangle", "Sawtooth"],
            command=lambda _: self.debounced_update()
        )
        shape_menu.set(shape)
        shape_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(shape_menu, "Select the waveform shape for the LFO.")

        # LFO frequency entry with tooltip
        ctk.CTkLabel(lfo_frame, text="Frequency (Hz)").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        freq_entry = ctk.CTkEntry(lfo_frame, width=100)
        freq_entry.insert(0, str(frequency))
        freq_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(freq_entry, "Set the frequency of the LFO in Hz.")

        # LFO depth slider with tooltip
        ctk.CTkLabel(lfo_frame, text="Depth").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        depth_slider = ctk.CTkSlider(lfo_frame, from_=0.0, to=2.0, command=lambda _: self.debounced_update())
        depth_slider.set(depth)
        depth_slider.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(depth_slider, "Set the depth (strength) of the LFO modulation.")

        # LFO target dropdown with tooltip
        ctk.CTkLabel(lfo_frame, text="Target").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        target_menu = ctk.CTkComboBox(
            lfo_frame, values=["Frequency", "Amplitude"],
            command=lambda _: self.debounced_update()
        )
        target_menu.set(target)
        target_menu.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        Tooltip(target_menu, "Select the parameter to modulate with the LFO.")

        # Remove button with tooltip
        remove_button = ctk.CTkButton(lfo_frame, text="Remove", command=lambda: self.remove_lfo(lfo_frame))
        remove_button.grid(row=4, column=0, columnspan=2, pady=5)
        Tooltip(remove_button, "Remove this LFO.")

        self.lfos.append({
            "frame": lfo_frame,
            "shape": shape_menu,
            "frequency": freq_entry,
            "depth": depth_slider,
            "target": target_menu,
        })
        self.debounced_update()

    def remove_lfo(self, lfo_frame):
        """Remove an LFO from the controls."""
        for lfo in self.lfos:
            if lfo["frame"] == lfo_frame:
                self.lfos.remove(lfo)
                break
        lfo_frame.destroy()
        self.debounced_update()


    def remove_effect(self, effect_frame):
        """Remove an effect from the effects chain."""
        for effect in self.effects:
            if effect["frame"] == effect_frame:
                self.effects.remove(effect)
                break
        effect_frame.destroy()
        self.debounced_update()


    def debounced_update(self, *args):
        """Update the waveform graphs after a short delay to prevent spamming updates."""
        if self.update_timer:
            self.update_timer.cancel()
        self.update_timer = Timer(0.3, self.update_graphs)
        self.update_timer.start()

    def update_graphs(self):
        """Regenerate and redraw the waveform and filter graphs."""
        waveform = self.generate_waveform()
        filtered_waveform = self.apply_filters(waveform)

        # Display a single wavelength or a few cycles for clarity
        max_cycles = 5
        t = np.linspace(0, self.duration, len(waveform), endpoint=False)
        # Calculate the cycles for displaying the waveform graph
        try:
            max_freq = max(
                [float(osc["frequency"].get()) for osc in self.oscillators if osc["frequency"].get().strip()]
                + [1]
            )
        except ValueError:
            max_freq = 1  # Fallback in case all frequencies are invalid
        cycles = int(self.sample_rate / max_freq)

        end_index = min(max_cycles * cycles, len(t))

        # Update Waveform Graph
        self.wave_ax.clear()
        self.wave_ax.plot(t[:end_index], waveform[:end_index], label="Raw Waveform", alpha=0.7)

        self.wave_ax.set_title("Waveform")
        self.wave_ax.legend()
        self.wave_ax.grid(True)

        # Update Filter Graph
        self.filter_ax.clear()
        self.filter_ax.plot(t[:end_index], filtered_waveform[:end_index], label="Filtered Waveform")
        self.filter_ax.set_title("Filter Output")
        self.filter_ax.legend()
        self.filter_ax.grid(True)

        # Refresh Canvas
        self.canvas.draw()


    def generate_waveform(self):
        """Generate waveform with LFO-modulated parameters."""
        duration = float(self.duration_entry.get())  # Get duration from the input field
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        waveform = np.zeros_like(t)

        for osc in self.oscillators:
            # Extract oscillator parameters
            waveform_type = osc["type"].get()
            try:
                base_freq = float(osc["frequency"].get())
            except ValueError:
                base_freq = 440.0  # Default frequency if invalid
            base_amp = osc["amplitude"].get()

            # Apply LFO to frequency
            freq_modulation = self.apply_lfo("Frequency", t)
            modulated_freq = base_freq * (1 + freq_modulation * 0.5)  # ±50% swing
            modulated_freq = np.clip(modulated_freq, 20, self.sample_rate / 2)  # Clamp frequency

            # Apply LFO to amplitude
            amp_modulation = self.apply_lfo("Amplitude", t)
            modulated_amp = base_amp * (1 + amp_modulation * 0.5)  # ±50% swing
            modulated_amp = np.clip(modulated_amp, 0.0, 1.0)  # Clamp amplitude

            # Calculate instantaneous phase for frequency modulation
            phase = np.cumsum(modulated_freq) * (2 * np.pi / self.sample_rate)

            # Generate waveform
            if waveform_type == "Sine":
                waveform += modulated_amp * np.sin(phase)
            elif waveform_type == "Square":
                waveform += modulated_amp * np.sign(np.sin(phase))
            elif waveform_type == "Sawtooth":
                waveform += modulated_amp * (2 * (phase / (2 * np.pi) % 1) - 1)
            elif waveform_type == "Triangle":
                waveform += modulated_amp * (2 * np.abs(2 * (phase / (2 * np.pi) % 1) - 1))

        # Normalize waveform
        max_val = np.max(np.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val

        # Apply master volume
        return waveform * self.volume_slider.get()



    def apply_filters(self, waveform):
        """Apply the active filters to the waveform."""
        for filter_ in self.filters:
            filter_type = filter_["type"].get()
            freq = filter_["frequency"].get()
            res = filter_["resonance"].get()
            if filter_type == "Low-pass":
                waveform = self.lowpass_filter(waveform, freq, res)
            elif filter_type == "High-pass":
                waveform = self.highpass_filter(waveform, freq, res)
            elif filter_type == "Band-pass":
                waveform = self.bandpass_filter(waveform, freq, res)
            elif filter_type == "Band-reject":
                waveform = self.band_reject_filter(waveform, freq, res)
        return waveform
    
    def apply_effects(self, waveform):
        """Apply the chain of effects to the waveform."""
        processed_waveform = waveform.copy()

        for effect in self.effects:
            effect_type = effect["type"].get()  # Get the selected effect type

            # Retrieve parameter values (call getter if callable, otherwise use the value directly)
            params = {
                key: getter() if callable(getter) else getter
                for key, getter in effect["params"].items()
            }



            # Apply the selected effect
            if effect_type == "Bitcrusher":
                processed_waveform = self.bitcrusher_effect(processed_waveform, params)
            elif effect_type == "Ring Modulation":
                processed_waveform = self.ring_modulation_effect(processed_waveform, params)
            elif effect_type == "Phaser":
                processed_waveform = self.phaser_effect(processed_waveform, params)
            elif effect_type == "Flanger":
                processed_waveform = self.flanger_effect(processed_waveform, params)
            elif effect_type == "Wavefolder":
                processed_waveform = self.wavefolder_effect(processed_waveform, params)
            elif effect_type == "Chorus":
                processed_waveform = self.chorus_effect(processed_waveform, params)

        return processed_waveform




    
    def apply_lfo(self, target, t):
        """Apply LFO modulation to the specified parameter."""
        modulation = np.zeros_like(t)
        for lfo in self.lfos:
            if lfo["target"].get() != target:
                continue

            # Get LFO parameters
            shape = lfo["shape"].get()
            freq = float(lfo["frequency"].get())  # Frequency of the LFO itself
            depth = lfo["depth"].get()  # Depth of modulation (scales -1 to 1 range)

            # Generate modulation signal
            if shape == "Sine":
                mod_signal = depth * np.sin(2 * np.pi * freq * t)
            elif shape == "Square":
                mod_signal = depth * np.sign(np.sin(2 * np.pi * freq * t))
            elif shape == "Triangle":
                mod_signal = depth * (2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1)
            elif shape == "Sawtooth":
                mod_signal = depth * (2 * (t * freq - np.floor(t * freq)))

            modulation += mod_signal  # Combine signals if multiple LFOs target the same parameter

        return modulation

    def lowpass_filter(self, waveform, cutoff, resonance):
        nyquist = 0.5 * self.sample_rate
        normal_cutoff = cutoff / nyquist
        b, a = butter(N=2, Wn=normal_cutoff, btype="low")
        return lfilter(b, a, waveform)

    def highpass_filter(self, waveform, cutoff, resonance):
        nyquist = 0.5 * self.sample_rate
        normal_cutoff = cutoff / nyquist
        b, a = butter(N=2, Wn=normal_cutoff, btype="high")
        return lfilter(b, a, waveform)

    def bandpass_filter(self, waveform, cutoff, resonance):
        nyquist = 0.5 * self.sample_rate
        low = max(0.01, (cutoff - resonance) / nyquist)
        high = min(1.0, (cutoff + resonance) / nyquist)
        b, a = butter(N=2, Wn=[low, high], btype="band")
        return lfilter(b, a, waveform)

    def band_reject_filter(self, waveform, cutoff, resonance):
        nyquist = 0.5 * self.sample_rate
        low = max(0.01, (cutoff - resonance) / nyquist)
        high = min(1.0, (cutoff + resonance) / nyquist)
        b, a = butter(N=2, Wn=[low, high], btype="bandstop")
        return lfilter(b, a, waveform)
    

    def bitcrusher_effect(self, waveform, params):
        """Apply a bitcrusher effect."""
        bit_depth = int(params.get("bit_depth", 8))  #  Ensure int type
        sample_rate_reduction = int(params.get("sample_rate_reduction", 4))  #  Ensure int type

        # Quantize the signal
        quantized_waveform = np.round(waveform * (2**(bit_depth - 1))) / (2**(bit_depth - 1))

        # Downsample the signal (Fix slice index issue)
        downsampled_waveform = quantized_waveform[::sample_rate_reduction]  #  Ensure int index
        return np.repeat(downsampled_waveform, sample_rate_reduction)[:len(waveform)]



    def ring_modulation_effect(self, waveform, params):
        """Apply ring modulation."""
        mod_freq = params.get("mod_freq", 100)  # Frequency of the modulator
        t = np.linspace(0, self.duration, len(waveform), endpoint=False)

        # Multiply the signal by a modulating sine wave
        modulator = np.sin(2 * np.pi * mod_freq * t)
        return waveform * modulator



    def phaser_effect(self, waveform, params):
        """Apply a phaser effect."""
        num_stages = int(params.get("num_stages", 4))  # Ensure num_stages is an integer
        sweep_freq = params.get("sweep_freq", 0.5)
        depth = params.get("depth", 0.5)

        t = np.linspace(0, self.duration, len(waveform), endpoint=False)
        lfo = depth * np.sin(2 * np.pi * sweep_freq * t)

        phaser_waveform = waveform.copy()
        for _ in range(num_stages):
            # Ensure cutoff frequency is within valid bounds
            cutoff = 500 + 1000 * lfo
            cutoff = np.clip(cutoff, 20, self.sample_rate / 2 - 1)  # Clamp cutoff frequency
            sos = butter(2, cutoff / (self.sample_rate / 2), btype='bandpass', output='sos')
            phaser_waveform = sosfilt(sos, phaser_waveform)
        return phaser_waveform


        
    def wavefolder_effect(self, waveform, params):
        """Apply wavefolding distortion."""
        threshold = params.get("threshold", 0.5)  # Folding threshold
        folded_waveform = np.abs(waveform)  # Start by folding negative values
        folded_waveform[folded_waveform > threshold] = 2 * threshold - folded_waveform[folded_waveform > threshold]
        return folded_waveform

    def flanger_effect(self, waveform, params):
        """Apply a flanger effect."""
        max_delay = int(params.get("max_delay", 0.005) * self.sample_rate)  # Max delay in samples
        rate = params.get("rate", 0.25)  # LFO rate for modulation

        t = np.linspace(0, self.duration, len(waveform), endpoint=False)
        lfo = max_delay * (1 + np.sin(2 * np.pi * rate * t)) / 2  # Modulate delay

        flanged_waveform = waveform.copy()
        for i in range(len(waveform)):
            delay = int(lfo[i])
            if i >= delay:
                flanged_waveform[i] += waveform[i - delay]
        return flanged_waveform / 2  # Normalize
    

    def chorus_effect(self, waveform, params):
        """Apply a chorus effect by layering detuned waveforms."""
        detune = params.get("detune", 0.02)
        delay = int(params.get("delay", 0.005) * self.sample_rate)
        num_voices = int(params.get("voices", 3))  # Ensure num_voices is an integer

        chorus_wave = waveform.copy()
        for i in range(num_voices):
            detune_factor = 1 + detune * (-1 if i % 2 == 0 else 1)  # Alternate detuning up and down

            # Generate detuned waveform
            detuned_wave = np.interp(
                np.linspace(0, len(waveform), int(len(waveform) * detune_factor)),
                np.arange(len(waveform)),
                waveform,
            )

            # Match length of detuned_wave to the original waveform
            if len(detuned_wave) > len(waveform):
                detuned_wave = detuned_wave[:len(waveform)]
            elif len(detuned_wave) < len(waveform):
                detuned_wave = np.pad(detuned_wave, (0, len(waveform) - len(detuned_wave)), mode="constant")

            # Add delayed detuned wave
            delayed_wave = np.pad(detuned_wave, (delay * i, 0), mode="constant")[:len(waveform)]
            chorus_wave += delayed_wave

        return chorus_wave / (num_voices + 1)  # Normalize output


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
        if self.preset_manager.preset_exists(preset_name, "Subtractive"):
            # Ask the user if they want to overwrite the existing preset
            confirm = messagebox.askyesno("Overwrite Preset", f"A preset named '{preset_name}' already exists. Do you want to overwrite it?")
            if not confirm:
                return  # User canceled the overwrite

        # Get the current settings, including the preset name
        preset_data = self.get_preset_data(preset_name)

        # Save the preset (this will overwrite if it already exists)
        self.preset_manager.save_preset(preset_name, "Subtractive", preset_data)

    def get_preset_data(self, preset_name):
        """Get the current settings of the subtractive synthesizer."""
        return {
            "type": "Subtractive",  # Explicitly include the synth type
            "name": preset_name,  # Dynamic preset name
            "volume": self.volume_slider.get(),
            "oscillators": [
                {
                    "type": osc["type"].get(),
                    "frequency": float(osc["frequency"].get()),
                    "amplitude": osc["amplitude"].get(),
                }
                for osc in self.oscillators
            ],
            "filters": [
                {
                    "type": filt["type"].get(),
                    "cutoff": filt["frequency"].get(),
                    "resonance": filt["resonance"].get(),
                }
                for filt in self.filters
            ],
            "effects": [
                {
                    "type": effect["type"].get(),
                    "params": {
                        key: value() if callable(value) else value
                        for key, value in effect["params"].items()
                    },
                }
                for effect in self.effects
            ],
            "lfos": [
                {
                    "shape": lfo["shape"].get(),
                    "frequency": float(lfo["frequency"].get()),
                    "depth": lfo["depth"].get(),
                    "target": lfo["target"].get(),
                }
                for lfo in self.lfos
            ],
        }

    def load_preset(self, preset_data):
        """Load a preset and update the UI."""
        if not preset_data:
            print("Error: Invalid preset data.")
            return

        # Update the loaded preset name
        self.loaded_preset_name = preset_data.get("name")

        print(f"Loading Subtractive Preset: {preset_data}")

        self.volume_slider.set(preset_data.get("volume", 0.5))

        # Load oscillators
        for osc in self.oscillators:
            osc["frame"].destroy()
        self.oscillators.clear()

        for osc in preset_data.get("oscillators", []):
            self.add_oscillator(osc["type"], osc["frequency"], osc["amplitude"])

        # Load filters
        for filt in self.filters:
            filt["frame"].destroy()
        self.filters.clear()

        for f in preset_data.get("filters", []):
            self.add_filter(f["type"], f["cutoff"], f["resonance"])

        # Load effects
        for effect in self.effects:
            effect["frame"].destroy()
        self.effects.clear()

        for e in preset_data.get("effects", []):
            self.add_effect(e["type"], e["params"])

        # Fix: Load LFOs properly
        for lfo in self.lfos:
            lfo["frame"].destroy()
        self.lfos.clear()

        for l in preset_data.get("lfos", []):
            print(f"Adding LFO: {l}")  # Debugging output
            self.add_lfo(l["shape"], float(l["frequency"]), float(l["depth"]), l["target"])

        self.update_graphs()




    def play_sound(self):
        """Play the generated waveform with effects."""
        # Generate the base waveform
        waveform = self.generate_waveform()

        # Apply filters
        waveform = self.apply_filters(waveform)

        # Apply effects
        waveform = self.apply_effects(waveform)

        # Normalize the waveform
        max_val = np.max(np.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val

        # Play the sound
        sd.play(waveform, samplerate=self.sample_rate)
        sd.wait()

