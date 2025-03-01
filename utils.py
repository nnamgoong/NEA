import customtkinter as ctk
import json
import numpy as np

class ScrollableFrame(ctk.CTkScrollableFrame):
    """A scrollable frame for adding multiple UI elements."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)


class MergeSort:
    @staticmethod
    def sort(arr, key, reverse=False):
        """Sort an array of tuples based on a specific key using merge sort."""
        if len(arr) <= 1:
            return arr

        mid = len(arr) // 2
        left = MergeSort.sort(arr[:mid], key, reverse)
        right = MergeSort.sort(arr[mid:], key, reverse)

        return MergeSort.merge(left, right, key, reverse)

    @staticmethod
    def merge(left, right, key, reverse):
        """Merge two sorted lists."""
        sorted_list = []
        i = j = 0

        while i < len(left) and j < len(right):
            if (key(left[i]) < key(right[j])) if not reverse else (key(left[i]) > key(right[j])):
                sorted_list.append(left[i])
                i += 1
            else:
                sorted_list.append(right[j])
                j += 1

        sorted_list.extend(left[i:])
        sorted_list.extend(right[j:])
        return sorted_list

class PresetExporterImporter:
    @staticmethod
    def export_preset(preset_data, file_path):
        """
        Export one or more presets to a text file.

        Args:
            preset_data (dict): The preset data to export.
            file_path (str): The path to save the text file.
        """
        try:
            print(f"Exporting Preset Data: {preset_data}")  # Debug statement
            with open(file_path, "w") as file:
                json.dump(preset_data, file, indent=4)
            print(f"Preset exported successfully to {file_path}")
        except Exception as e:
            print(f"Error exporting preset: {e}")

    @staticmethod
    def import_preset(file_path):
        """
        Import a preset from a text file.

        Args:
            file_path (str): The path to the text file containing the preset.

        Returns:
            dict: The imported preset data, or None if an error occurred.
        """
        try:
            with open(file_path, "r") as file:
                preset_data = json.load(file)
            print(f"Preset imported successfully from {file_path}")
            return preset_data
        except Exception as e:
            print(f"Error importing preset: {e}")
            return None
        

class FFT:
    @staticmethod
    def fft(x: np.ndarray) -> np.ndarray:
        """
        Compute the Fast Fourier Transform (FFT) of a 1D array using the Cooley-Tukey algorithm.
        This implementation assumes the input length is a power of two.

        Args:
            x (np.ndarray): Input array of complex numbers.

        Returns:
            np.ndarray: The FFT of the input array.
        """
        N = len(x)
        if N <= 1:
            return x

        # Ensure N is a power of two by padding with zeros
        if N & (N - 1) != 0:
            next_power_of_two = 2 ** (int(np.log2(N)) + 1)
            x = np.pad(x, (0, next_power_of_two - N), mode='constant')

        # Split into even and odd indices
        even = FFT.fft(x[::2])
        odd = FFT.fft(x[1::2])

        # Combine results
        T = [np.exp(-2j * np.pi * k / N) * odd[k] for k in range(N // 2)]
        return np.array([even[k] + T[k] for k in range(N // 2)] +
                        [even[k] - T[k] for k in range(N // 2)])

    @staticmethod
    def ifft(X: np.ndarray) -> np.ndarray:
        """
        Compute the Inverse Fast Fourier Transform (IFFT) of a 1D array.
        This implementation assumes the input length is a power of two.

        Args:
            X (np.ndarray): Input array of complex numbers.

        Returns:
            np.ndarray: The IFFT of the input array.
        """
        N = len(X)
        if N <= 1:
            return X

        # Ensure N is a power of two by padding with zeros
        if N & (N - 1) != 0:
            next_power_of_two = 2 ** (int(np.log2(N)) + 1)
            X = np.pad(X, (0, next_power_of_two - N), mode='constant')

        # Split into even and odd indices
        even = FFT.ifft(X[::2])
        odd = FFT.ifft(X[1::2])

        # Combine results
        T = [np.exp(2j * np.pi * k / N) * odd[k] for k in range(N // 2)]
        return np.array([(even[k] + T[k]) / 2 for k in range(N // 2)] +
                        [(even[k] - T[k]) / 2 for k in range(N // 2)])

    @staticmethod
    def rfft(x: np.ndarray) -> np.ndarray:
        """
        Compute the real-valued FFT of a 1D array.
        This implementation matches np.fft.rfft behavior.

        Args:
            x (np.ndarray): Input array of real numbers.

        Returns:
            np.ndarray: The real-valued FFT of the input array.
        """
        N = len(x)
        if N <= 1:
            return np.array([complex(val) for val in x])

        # Ensure N is a power of two by padding with zeros
        if N & (N - 1) != 0:
            next_power_of_two = 2 ** (int(np.log2(N)) + 1)
            x = np.pad(x, (0, next_power_of_two - N), mode='constant')

        # Convert real input to complex
        x_complex = np.array([complex(val) for val in x])

        # Compute FFT
        fft_result = FFT.fft(x_complex)

        # Return only the non-redundant part (first half + 1)
        return fft_result[:N // 2 + 1]

    @staticmethod
    def rfftfreq(n, d=1.0):
        """
        Return the Discrete Fourier Transform sample frequencies
        (for usage with rfft, irfft).

        Args:
            n (int): Window length.
            d (float): Sample spacing (inverse of the sampling rate). Default is 1.0.

        Returns:
            np.ndarray: Array of length n//2 + 1 containing the sample frequencies.
        """
        if not isinstance(n, int) or n <= 0:
            raise ValueError("n must be a positive integer")
        if not isinstance(d, (int, float)) or d <= 0:
            raise ValueError("d must be a positive number")

        val = 1.0 / (n * d)
        N = n // 2 + 1
        results = np.arange(0, N, dtype=int)
        return results * val

    @staticmethod
    def irfft(X: np.ndarray) -> np.ndarray:
        """
        Compute the inverse real-valued FFT of a 1D array.
        This implementation matches np.fft.irfft behavior.

        Args:
            X (np.ndarray): Input array of complex numbers.

        Returns:
            np.ndarray: The inverse real-valued FFT of the input array.
        """
        N = len(X)
        if N <= 1:
            return np.array([complex(val) for val in X])

        # Ensure N is a power of two by padding with zeros
        if N & (N - 1) != 0:
            next_power_of_two = 2 ** (int(np.log2(N)) + 1)
            X = np.pad(X, (0, next_power_of_two - N), mode='constant')

        # Compute IFFT
        ifft_result = FFT.ifft(X)

        # Return only the real part
        return np.real(ifft_result)