import customtkinter as ctk
import tkinter as tk
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from tkinter import messagebox

from additive_synth import AdditiveSynth
from subtractive_synth import SubtractiveSynth
from login_system import LoginSystem
from preset_manager import PresetManager, CommunityPresetManager


class SynthApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Synthesizer Application")
        self.geometry("1200x700")  # Standard 16:9 ratio window
        
        # Configure grid for consistent scaling
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sample_rate = 32768
        self.duration = 1.0
        self.create_menu_bar()
        self.create_login_system()

    def create_menu_bar(self):
        """Create a menu bar with an Exit option."""
        # Use tk.Menu for the menu bar
        self.menu_bar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.exit_program)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Configure the menu bar
        self.config(menu=self.menu_bar)

    def exit_program(self):
        """Exit the program."""
        self.quit()  # Exit the application

    def create_login_system(self):
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(fill="both", expand=True)
        self.login_system = LoginSystem(self.login_frame, self.on_login_success)

    def on_login_success(self, user_id):
        self.user_id = user_id
        self.login_frame.pack_forget()
        self.create_tabs()

    def create_tabs(self):
        """Create the tabs for the synthesizer application."""
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True)

        self.additive_tab = self.tab_view.add("Additive Synth")
        self.subtractive_tab = self.tab_view.add("Subtractive Synth")
        self.presets_tab = self.tab_view.add("Presets")
        self.community_tab = self.tab_view.add("Community Presets")

        # Initialize the preset manager and community preset manager
        self.create_preset_manager()
        self.create_community_preset_manager()

        # Create the UI for each tab
        self.create_additive_synth_ui()
        self.create_subtractive_synth_ui()

        
    def check_tab_selection(self):
        current_tab = self.tab_view.get()
        if current_tab == "Presets":
            self.preset_manager.refresh_preset_list()

        # Schedule the function to run again after 500ms
        self.after(500, self.check_tab_selection)

    def on_tab_change(self, event=None):
        if self.tab_view.get() == "Presets":
            self.preset_manager.refresh_preset_list()  # Refresh preset list dynamically

    def create_additive_synth_ui(self):
        # Clear existing widgets in the additive tab
        for widget in self.additive_tab.winfo_children():
            widget.destroy()

        # Create and assign the AdditiveSynth instance
        self.additive_synth = AdditiveSynth(
            self.additive_tab,
            self.sample_rate,
            self.duration,
            self.preset_manager,  # Use the preset_manager attribute
            self.user_id
        )

    def create_subtractive_synth_ui(self):
        # Clear existing widgets in the subtractive tab
        for widget in self.subtractive_tab.winfo_children():
            widget.destroy()

        # Create and assign the SubtractiveSynth instance
        self.subtractive_synth = SubtractiveSynth(
            self.subtractive_tab,
            sample_rate=self.sample_rate,
            duration=self.duration,
            update_presets_callback=self.update_presets,
            user_id=self.user_id,
            preset_manager=self.preset_manager  # Use the preset_manager attribute
        )

    def create_preset_manager(self):
        """Initialize the preset manager."""
        self.preset_manager = PresetManager(self.user_id, self.presets_tab, self)

    def create_community_preset_manager(self):
        """Initialize the community preset manager."""
        self.community_preset_manager = CommunityPresetManager(
            self.community_tab,  # parent (the Community Presets tab)
            self.user_id,        # user_id
            self                 # app (reference to the main SynthApp)
        )
    def navigate_to_synth(self, synth_type, preset_data):
        """Navigate to the appropriate synth UI and load the preset data."""
        if synth_type == "Additive":
            if self.tab_view.get() != "Additive Synth":  # Prevent infinite switching
                self.tab_view.set("Additive Synth")
            self.additive_synth.load_preset(preset_data)  

        elif synth_type == "Subtractive":
            if self.tab_view.get() != "Subtractive Synth":  # Prevent infinite switching
                self.tab_view.set("Subtractive Synth")
            self.subtractive_synth.load_preset(preset_data)    

        else:
            print(f"Error: Unknown synth type '{synth_type}'.")

    def update_presets(self):
        self.preset_manager.refresh_presets()

if __name__ == "__main__":
    print("start")
    app = SynthApp()
    app.mainloop()