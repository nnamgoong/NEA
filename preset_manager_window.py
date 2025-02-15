import customtkinter as ctk
from tkinter import Listbox

class PresetManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent, preset_manager, user_id, synthesis_mode):
        super().__init__(parent)
        self.title("Preset Manager")
        self.geometry("500x400")
        self.preset_manager = preset_manager
        self.user_id = user_id
        self.synthesis_mode = synthesis_mode.lower()  # Ensure lowercase

        # UI Components
        self.preset_listbox = Listbox(self, height=15, width=40)
        self.preset_listbox.pack(pady=10)

        self.load_button = ctk.CTkButton(self, text="Load Preset", command=self.load_preset)
        self.load_button.pack(pady=5)

        self.delete_button = ctk.CTkButton(self, text="Delete Preset", command=self.delete_preset)
        self.delete_button.pack(pady=5)

        self.refresh_button = ctk.CTkButton(self, text="Refresh", command=self.populate_preset_list)
        self.refresh_button.pack(pady=5)

        self.populate_preset_list()


    def populate_preset_list(self):
        """Populate the listbox with presets for the current user and mode."""
        try:
            print(f"Populating presets for mode: {self.synthesis_mode}")
            self.preset_listbox.delete(0, "end")  # Clear the listbox
            presets = self.preset_manager.get_preset_names(self.user_id, self.synthesis_mode)
            for preset_name in presets:
                self.preset_listbox.insert("end", preset_name)
        except Exception as e:
            print(f"Error populating presets: {e}")

    def load_preset(self):
        """Load the selected preset."""
        selected_index = self.preset_listbox.curselection()
        if selected_index:
            preset_name = self.preset_listbox.get(selected_index)
            preset = self.preset_manager.load_preset(self.user_id, preset_name, self.synthesis_mode)
            if preset:
                # Pass the loaded preset back to the main application
                self.master.load_preset_callback(preset)
                ctk.CTkLabel(self, text=f"Preset '{preset_name}' loaded successfully.").pack()

    def delete_preset(self):
        """Delete the selected preset."""
        selected_index = self.preset_listbox.curselection()
        if selected_index:
            preset_name = self.preset_listbox.get(selected_index)
            deleted = self.preset_manager.delete_preset(self.user_id, preset_name, self.synthesis_mode)
            if deleted:
                self.populate_preset_list()
                ctk.CTkLabel(self, text=f"Preset '{preset_name}' deleted successfully.").pack()
            else:
                ctk.CTkLabel(self, text=f"Error deleting preset '{preset_name}'.").pack()
