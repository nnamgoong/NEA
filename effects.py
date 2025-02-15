import numpy as np
from scipy.signal import butter, sosfilt

class Effects():
    def __init__(self, sample_rate, duration):
        self.sample_rate = sample_rate
        self.duration = duration
    def bitcrusher_effect(self, waveform, params):
        """Apply a bitcrusher effect."""
        bit_depth = params.get("bit_depth", 8)  # Number of bits (e.g., 8 bits)
        sample_rate_reduction = params.get("sample_rate_reduction", 4)  # Factor to downsample the signal

        # Quantize the signal
        quantized_waveform = np.round(waveform * (2**(bit_depth - 1))) / (2**(bit_depth - 1))
        
        # Downsample the signal
        downsampled_waveform = quantized_waveform[::sample_rate_reduction]
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
            cutoff = 500 + 1000 * lfo
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
