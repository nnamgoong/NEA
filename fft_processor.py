import numpy as np

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
