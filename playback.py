# playback.py
import sounddevice as sd
import numpy as np

# Global variable to track playback status
current_playback = None

def start_playback(waveform, sample_rate):
    """
    Start playing the waveform.
    Parameters:
    - waveform: The audio waveform as a NumPy array.
    - sample_rate: The playback sample rate in Hz.
    """
    global current_playback
    stop_playback()  # Ensure no other playback is running

    # Normalize waveform to avoid clipping
    normalized_waveform = waveform / np.max(np.abs(waveform))
    current_playback = sd.OutputStream(samplerate=sample_rate, channels=1)
    current_playback.start()
    current_playback.write(normalized_waveform.astype(np.float32))

def stop_playback():
    """
    Stop any ongoing playback.
    """
    global current_playback
    if current_playback:
        current_playback.stop()
        current_playback.close()
        current_playback = None
