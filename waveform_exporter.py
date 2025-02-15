import wave
import numpy as np

class WaveformExporter:
    @staticmethod
    def export_to_wav(waveform, sample_rate, filename="output.wav"):
        waveform_int16 = np.int16(waveform / np.max(np.abs(waveform)) * 32767)
        with wave.open(filename, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(waveform_int16.tobytes())
