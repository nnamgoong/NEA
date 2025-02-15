import sqlite3
import json
import customtkinter as ctk
from tkinter import filedialog

from utils import MergeSort, PresetExporterImporter


class PresetManager:
    def __init__(self, user_id, parent, app, db_path="synth.db"):
        self.db_path = db_path
        self.user_id = user_id
        self.parent = parent  # Presets tab (UI parent)
        self.app = app  # Reference to the main SynthApp
        self.create_preset_ui()

        
            
    def save_preset(self, preset_name, preset_type, preset_data):
        """Save a preset (either additive or subtractive) to the database."""
        print(f"Saving {preset_type} preset: {preset_name}")  # Debug statement
        print(f"Preset Data: {preset_data}")  # Debug statement

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            if preset_type == "Additive":
                cursor.execute("""
                    INSERT INTO AdditivePresets (user_id, name, base_frequency, sample_rate, duration, volume, tone, num_harmonics, attack, decay, sustain, release)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id, preset_name, preset_data["base_frequency"], preset_data["sample_rate"], preset_data["duration"],
                    preset_data["volume"], preset_data["tone"], preset_data["num_harmonics"], preset_data["adsr"]["attack"],
                    preset_data["adsr"]["decay"], preset_data["adsr"]["sustain"], preset_data["adsr"]["release"]
                ))
                connection.commit()  # Ensure changes are committed
                print("Additive preset inserted successfully!")  # Debug statement
                
            elif preset_type == "Subtractive":
            
                    # Save the main preset data
                    cursor.execute("""
                        INSERT INTO SubtractivePresets (user_id, name, volume)
                        VALUES (?, ?, ?)
                    """, (self.user_id, preset_name, preset_data["volume"]))

                    # Get the ID of the newly created preset
                    preset_id = cursor.lastrowid

                    # Save oscillators
                    for osc in preset_data["oscillators"]:
                        cursor.execute("""
                            INSERT INTO SubtractivePresetOscillators (preset_id, type, frequency, amplitude)
                            VALUES (?, ?, ?, ?)
                        """, (preset_id, osc["type"], osc["frequency"], osc["amplitude"]))

                    # Save filters
                    for filt in preset_data["filters"]:
                        cursor.execute("""
                            INSERT INTO SubtractivePresetFilters (preset_id, filter_type, cutoff_frequency, resonance)
                            VALUES (?, ?, ?, ?)
                        """, (preset_id, filt["type"], filt["cutoff"], filt["resonance"]))

                    # Save effects
                    for effect in preset_data["effects"]:
                        # Fetch effect ID from the database
                        cursor.execute("SELECT Eid FROM Effects WHERE name = ?", (effect["type"],))
                        result = cursor.fetchone()

                        if result:
                            effect_id = result[0]  # Use the valid effect ID
                        else:
                            # If the effect is missing, insert it first
                            cursor.execute("INSERT INTO Effects (name, description) VALUES (?, ?)", (effect["type"], "Custom Effect"))
                            effect_id = cursor.lastrowid  # Get the new effect ID

                        # Save the effect parameters
                        cursor.execute("""
                            INSERT INTO SubtractivePresetEffects (preset_id, effect_id, parameters)
                            VALUES (?, ?, ?)
                        """, (preset_id, effect_id, json.dumps(effect["params"])))

                    # Save LFOs
                    for lfo in preset_data["lfos"]:
                        cursor.execute("""
                            INSERT INTO SubtractivePresetLFOs (preset_id, shape, frequency, depth, target)
                            VALUES (?, ?, ?, ?, ?)
                        """, (preset_id, lfo["shape"], lfo["frequency"], lfo["depth"], lfo["target"]))

                    connection.commit()  # Commit all changes
                    print(f"Subtractive preset '{preset_name}' saved successfully!")

        except sqlite3.Error as e:
            print(f"ERROR: Database error: {e}")  # Print any database errors

        finally:
            connection.close()  # Ensure connection closes to avoid locking issues

        self.refresh_preset_list()  # Refresh the UI to show the new preset




            
    def list_presets(self, sort_by="name"):
        """Retrieve a sorted list of all presets for the user."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        
        # Debug: Check Additive presets
        cursor.execute("SELECT name, 'Additive' as type, created_at, last_updated FROM AdditivePresets WHERE user_id = ?", (self.user_id,))
        additive_presets = cursor.fetchall()
        print("Additive Presets:", additive_presets)  # Debug statement

        # Debug: Check Subtractive presets
        cursor.execute("SELECT name, 'Subtractive' as type, created_at, last_updated FROM SubtractivePresets WHERE user_id = ?", (self.user_id,))
        subtractive_presets = cursor.fetchall()
        print("Subtractive Presets:", subtractive_presets)  # Debug statement

        # Combine the results
        presets = additive_presets + subtractive_presets
        
        connection.close()

        # Debug: Print the combined presets
        print("Combined Presets:", presets)  # Debug statement

        # Sort the presets based on the selected sort type
        if sort_by == "name":
            presets = sorted(presets, key=lambda x: x[0])  # Sort by name
        elif sort_by == "created_at":
            presets = sorted(presets, key=lambda x: x[2])  # Sort by creation date
        elif sort_by == "last_updated":
            presets = sorted(presets, key=lambda x: x[3])  # Sort by last updated date

        return presets
    
    def delete_preset(self, preset_name):
        """Delete a preset by name."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            # Delete from AdditivePresets
            cursor.execute("DELETE FROM AdditivePresets WHERE user_id = ? AND name = ?", (self.user_id, preset_name))
            
            # Delete from SubtractivePresets
            cursor.execute("DELETE FROM SubtractivePresets WHERE user_id = ? AND name = ?", (self.user_id, preset_name))
            
            connection.commit()  # Commit the changes
            print(f"Preset '{preset_name}' deleted successfully!")
        except sqlite3.Error as e:
            print(f"Error deleting preset: {e}")
        finally:
            connection.close()  # Ensure the connection is closed

        self.refresh_preset_list()  # Refresh the UI
            
    def create_preset_ui(self):
        """Create the UI for managing presets inside the Presets tab."""
        self.sort_var = ctk.StringVar(value="name")
        ctk.CTkLabel(self.parent, text="Sort by:").pack(pady=5)
        self.sort_menu = ctk.CTkComboBox(self.parent, values=["name", "created_at", "last_updated"], variable=self.sort_var, command=self.refresh_preset_list)
        self.sort_menu.pack(pady=5)
        
        self.preset_listbox = ctk.CTkFrame(self.parent)
        self.preset_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        


        # Add Import/Export buttons
        button_frame = ctk.CTkFrame(self.parent)
        button_frame.pack(fill="x", padx=10, pady=10)

        export_button = ctk.CTkButton(button_frame, text="Export Preset", command=self.export_preset)
        export_button.pack(side="left", padx=5)

        import_button = ctk.CTkButton(button_frame, text="Import Preset", command=self.import_preset)
        import_button.pack(side="left", padx=5)

        self.refresh_preset_list()

    def refresh_preset_list(self, *args):
        """Refresh the preset list inside the UI without infinite recursion."""
        # print("Refreshing preset list...")  # Comment out or remove this line
        if hasattr(self, "updating") and self.updating:
            return  # Prevent recursive refreshes
        self.updating = True

        # Clear existing widgets in the preset listbox
        for widget in self.preset_listbox.winfo_children():
            widget.destroy()

        # Get the presets sorted by the selected sort type
        presets = self.list_presets(self.sort_var.get())

        # Add presets to the listbox
        for idx, (name, preset_type, created_at, last_updated) in enumerate(presets, start=1):
            frame = ctk.CTkFrame(self.preset_listbox)
            frame.pack(fill="x", padx=5, pady=2)

            # Add the preset name
            ctk.CTkLabel(frame, text=name, width=150).grid(row=idx, column=0, padx=5, pady=5)

            # Add the preset type
            ctk.CTkLabel(frame, text=preset_type, width=100).grid(row=idx, column=1, padx=5, pady=5)

            # Add the created date
            ctk.CTkLabel(frame, text=created_at, width=150).grid(row=idx, column=2, padx=5, pady=5)

            # Add the last updated date
            ctk.CTkLabel(frame, text=last_updated, width=150).grid(row=idx, column=3, padx=5, pady=5)

            # Add Load and Delete buttons
            button_frame = ctk.CTkFrame(frame)
            button_frame.grid(row=idx, column=4, padx=5, pady=5)

            load_button = ctk.CTkButton(button_frame, text="Load", command=lambda n=name, t=preset_type: self.load_preset(n, t))
            load_button.pack(side="left", padx=2)

            delete_button = ctk.CTkButton(button_frame, text="Delete", command=lambda n=name: self.delete_preset(n))
            delete_button.pack(side="left", padx=2)

        self.updating = False
        
    def load_preset(self, preset_name, preset_type):
        """Load the selected preset and apply it to the corresponding synth UI."""
        print(f"Loading preset: {preset_name} ({preset_type})")
            
        # Fetch preset data
        preset_data = self.load_preset_data(preset_name, preset_type)
            
        if not preset_data:
            print("Error: Preset not found.")
            return
            
            # Correctly call navigate_to_synth() from SynthApp
        self.app.navigate_to_synth(preset_type, preset_data)

    def load_preset_data(self, preset_name, preset_type):
        """Retrieve preset data from the database."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        if preset_type == "Additive":
            cursor.execute("""
                SELECT base_frequency, sample_rate, duration, volume, tone, num_harmonics, attack, decay, sustain, release
                FROM AdditivePresets
                WHERE user_id = ? AND name = ?
            """, (self.user_id, preset_name))
            result = cursor.fetchone()

            if not result:
                print(f"Error: Additive Preset '{preset_name}' not found.")
                return None

            # Extract the data
            base_frequency, sample_rate, duration, volume, tone, num_harmonics, attack, decay, sustain, release = result

            return {
                "name": preset_name,
                "base_frequency": base_frequency,
                "sample_rate": sample_rate,
                "duration": duration,
                "volume": volume,
                "tone": tone,
                "num_harmonics": num_harmonics,
                "adsr": {
                    "attack": attack,
                    "decay": decay,
                    "sustain": sustain,
                    "release": release,
                },
            }

        elif preset_type == "Subtractive":
            cursor.execute("""
                SELECT Sid, volume FROM SubtractivePresets 
                WHERE user_id = ? AND name = ?
            """, (self.user_id, preset_name))
            preset = cursor.fetchone()
            
            if not preset:
                print(f"Error: Subtractive Preset '{preset_name}' not found.")
                return None
            
            preset_id, volume = preset

            # Retrieve filters
            cursor.execute("""
                SELECT filter_type, cutoff_frequency, resonance FROM SubtractivePresetFilters 
                WHERE preset_id = ?
            """, (preset_id,))
            filters = [{"type": row[0], "cutoff": row[1], "resonance": row[2]} for row in cursor.fetchall()]

            # Retrieve oscillators
            cursor.execute("""
                SELECT type, frequency, amplitude FROM SubtractivePresetOscillators 
                WHERE preset_id = ?
            """, (preset_id,))
            oscillators = [{"type": row[0], "frequency": row[1], "amplitude": row[2]} for row in cursor.fetchall()]

            # Retrieve effects
            cursor.execute("""
                SELECT e.name, spe.parameters FROM SubtractivePresetEffects spe
                JOIN Effects e ON spe.effect_id = e.Eid
                WHERE spe.preset_id = ?
            """, (preset_id,))
            effects = [{"type": row[0], "params": json.loads(row[1])} for row in cursor.fetchall()]

            # Retrieve LFOs (fix: ensure correct SQL column names)
            cursor.execute("""
                SELECT shape, frequency, depth, target FROM SubtractivePresetLFOs
                WHERE preset_id = ?
            """, (preset_id,))
            lfos = [{"shape": row[0], "frequency": row[1], "depth": row[2], "target": row[3]} for row in cursor.fetchall()]

            return {
                "name": preset_name,
                "volume": volume,
                "oscillators": oscillators,
                "filters": filters,
                "effects": effects,
                "lfos": lfos  # Fix: Ensure LFOs are retrieved
            }
            
    def export_preset(self):
        """Export the selected preset to a text file."""
        selected_preset_name = self.preset_var.get()
        if not selected_preset_name:
            print("Error: No preset selected.")
            return

        preset_type = self.get_preset_type(selected_preset_name)
        if not preset_type:
            print("Error: Preset type not found.")
            return

        preset_data = self.load_preset_data(selected_preset_name, preset_type)
        if not preset_data:
            print("Error: Preset not found.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            PresetExporterImporter.export_preset(preset_data, file_path)

    def import_preset(self):
        """Import a preset from a text file."""
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            preset_data = PresetExporterImporter.import_preset(file_path)
            if preset_data:
                self.app.navigate_to_synth(preset_data.get("type", "Subtractive"), preset_data)
                    
    def get_selected_preset(self):
        """Get the name and type of the currently selected preset."""
        for widget in self.preset_listbox.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkLabel):
                        preset_name, preset_type = child.cget("text").split(" (")
                        preset_type = preset_type.rstrip(")")
                        return preset_name, preset_type
        return None, None
    def get_preset_type(self, preset_name):
        """Get the type of a preset by its name."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("SELECT 'Additive' FROM AdditivePresets WHERE name = ? AND user_id = ?", (preset_name, self.user_id))
        if cursor.fetchone():
            connection.close()
            return "Additive"

        cursor.execute("SELECT 'Subtractive' FROM SubtractivePresets WHERE name = ? AND user_id = ?", (preset_name, self.user_id))
        if cursor.fetchone():
            connection.close()
            return "Subtractive"

        connection.close()
        return None