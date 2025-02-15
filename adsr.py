import numpy as np

class ADSR:
    def __init__(self, attack, decay, sustain, release, sample_rate):
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.sample_rate = sample_rate

    def generate_envelope(self, duration):
        total_samples = int(duration * self.sample_rate)
        attack_samples = int(self.attack * self.sample_rate)
        decay_samples = int(self.decay * self.sample_rate)
        sustain_samples = max(0, total_samples - attack_samples - decay_samples - int(self.release * self.sample_rate))
        release_samples = total_samples - attack_samples - decay_samples - sustain_samples

        attack_env = np.linspace(0, 1, attack_samples)
        decay_env = np.linspace(1, self.sustain, decay_samples)
        sustain_env = np.full(sustain_samples, self.sustain)
        release_env = np.linspace(self.sustain, 0, release_samples)

        envelope = np.concatenate([attack_env, decay_env, sustain_env, release_env])
        return envelope[:total_samples]
