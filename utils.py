import customtkinter as ctk
import json

class ScrollableFrame(ctk.CTkScrollableFrame):
    """A scrollable frame for adding multiple UI elements."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)


class MergeSort:
    @staticmethod
    def sort(arr, key):
        """Sort an array of tuples based on a specific key using merge sort."""
        if len(arr) <= 1:
            return arr

        mid = len(arr) // 2
        left = MergeSort.sort(arr[:mid], key)
        right = MergeSort.sort(arr[mid:], key)

        return MergeSort.merge(left, right, key)

    @staticmethod
    def merge(left, right, key):
        """Merge two sorted lists."""
        sorted_list = []
        i = j = 0

        while i < len(left) and j < len(right):
            if key(left[i]) < key(right[j]):
                sorted_list.append(left[i])
                i += 1
            else:
                sorted_list.append(right[j])
                j += 1

        sorted_list.extend(left[i:])
        sorted_list.extend(right[j:])
        return sorted_list


class PresetExporterImporter:
    """Utility class for exporting and importing presets as text files."""
    @staticmethod
    def export_preset(preset_data, file_path):
        """
        Export one or more presets to a text file.

        Args:
            preset_data (list or dict): The preset data to export.
            file_path (str): The path to save the text file.
        """
        try:
            with open(file_path, "w") as file:
                json.dump(preset_data, file, indent=4)
            print(f"Preset(s) exported successfully to {file_path}")
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