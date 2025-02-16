import sqlite3
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
from utils import MergeSort, PresetExporterImporter


class PresetManager:
    def __init__(self, user_id, parent, app, db_path="synth.db"):
        self.db_path = db_path
        self.user_id = user_id
        self.parent = parent  # Presets tab (UI parent)
        self.app = app  # Reference to the main SynthApp
        self.create_preset_ui()

        
                
    def save_preset(self, preset_name, preset_type, preset_data):
        """Save or update a preset in the database."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Check if the preset already exists
            if preset_type == "Additive":
                cursor.execute("SELECT name FROM AdditivePresets WHERE user_id = ? AND name = ?", (self.user_id, preset_name))
            elif preset_type == "Subtractive":
                cursor.execute("SELECT name FROM SubtractivePresets WHERE user_id = ? AND name = ?", (self.user_id, preset_name))

            preset_exists = cursor.fetchone() is not None

            if preset_type == "Additive":
                if preset_exists:
                    # Update existing preset
                    cursor.execute("""
                        UPDATE AdditivePresets
                        SET base_frequency = ?, sample_rate = ?, duration = ?, volume = ?, tone = ?, num_harmonics = ?, attack = ?, decay = ?, sustain = ?, release = ?, last_updated = ?
                        WHERE user_id = ? AND name = ?
                    """, (
                        preset_data["base_frequency"], preset_data["sample_rate"], preset_data["duration"],
                        preset_data["volume"], preset_data["tone"], preset_data["num_harmonics"], preset_data["adsr"]["attack"],
                        preset_data["adsr"]["decay"], preset_data["adsr"]["sustain"], preset_data["adsr"]["release"], current_time,
                        self.user_id, preset_name
                    ))
                else:
                    # Insert new preset
                    cursor.execute("""
                        INSERT INTO AdditivePresets (user_id, name, base_frequency, sample_rate, duration, volume, tone, num_harmonics, attack, decay, sustain, release, created_at, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.user_id, preset_name, preset_data["base_frequency"], preset_data["sample_rate"], preset_data["duration"],
                        preset_data["volume"], preset_data["tone"], preset_data["num_harmonics"], preset_data["adsr"]["attack"],
                        preset_data["adsr"]["decay"], preset_data["adsr"]["sustain"], preset_data["adsr"]["release"], current_time, current_time
                    ))

            elif preset_type == "Subtractive":
                if preset_exists:
                    # Update existing preset
                    cursor.execute("""
                        UPDATE SubtractivePresets
                        SET volume = ?, last_updated = ?
                        WHERE user_id = ? AND name = ?
                    """, (preset_data["volume"], current_time, self.user_id, preset_name))

                    # Get the preset ID
                    cursor.execute("SELECT Sid FROM SubtractivePresets WHERE user_id = ? AND name = ?", (self.user_id, preset_name))
                    preset_id = cursor.fetchone()[0]

                    # Delete existing components (oscillators, filters, effects, LFOs)
                    cursor.execute("DELETE FROM SubtractivePresetOscillators WHERE preset_id = ?", (preset_id,))
                    cursor.execute("DELETE FROM SubtractivePresetFilters WHERE preset_id = ?", (preset_id,))
                    cursor.execute("DELETE FROM SubtractivePresetEffects WHERE preset_id = ?", (preset_id,))
                    cursor.execute("DELETE FROM SubtractivePresetLFOs WHERE preset_id = ?", (preset_id,))

                    # Save updated components
                    self._save_subtractive_components(cursor, preset_id, preset_data)
                else:
                    # Insert new preset
                    cursor.execute("""
                        INSERT INTO SubtractivePresets (user_id, name, volume, created_at, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (self.user_id, preset_name, preset_data["volume"], current_time, current_time))

                    # Get the ID of the newly created preset
                    preset_id = cursor.lastrowid

                    # Save oscillators, filters, effects, and LFOs
                    self._save_subtractive_components(cursor, preset_id, preset_data)

            connection.commit()
            print(f"Preset '{preset_name}' {'updated' if preset_exists else 'saved'} successfully!")
        except sqlite3.Error as e:
            print(f"ERROR: Database error: {e}")
        finally:
            connection.close()

        # Refresh the preset list after saving
        self.refresh_preset_list()



                
    def list_presets(self, sort_by="name"):
        """Retrieve a sorted list of all presets for the user."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        # Retrieve additive presets
        cursor.execute("""
            SELECT name, 'Additive' as type, created_at, last_updated
            FROM AdditivePresets
            WHERE user_id = ?
        """, (self.user_id,))
        additive_presets = cursor.fetchall()

        # Retrieve subtractive presets
        cursor.execute("""
            SELECT name, 'Subtractive' as type, created_at, last_updated
            FROM SubtractivePresets
            WHERE user_id = ?
        """, (self.user_id,))
        subtractive_presets = cursor.fetchall()

        # Combine the results
        presets = additive_presets + subtractive_presets

        connection.close()

        # Sort the presets based on the selected sort type
        if sort_by == "name":
            presets = sorted(presets, key=lambda x: x[0])  # Sort by name (ascending)
        elif sort_by == "created_at":
            presets = sorted(presets, key=lambda x: x[2], reverse=True)  # Sort by creation date (latest first)
        elif sort_by == "last_updated":
            presets = sorted(presets, key=lambda x: x[3], reverse=True)  # Sort by last updated date (latest first)

        return presets
    

    def delete_preset(self, preset_name):
        """Delete a preset by name after confirming with the user."""
        # Ask for confirmation before deleting
        confirm = messagebox.askyesno("Delete Preset", f"Are you sure you want to delete '{preset_name}'?")
        if not confirm:
            return  # User canceled the deletion

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
            connection.close()

        # Refresh the preset list after deleting
        self.refresh_preset_list()

            
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
        """Refresh the preset list inside the UI with headers and checkboxes."""
        # Clear existing widgets in the preset listbox
        for widget in self.preset_listbox.winfo_children():
            widget.destroy()

        # Add headers
        header_frame = ctk.CTkFrame(self.preset_listbox)
        header_frame.pack(fill="x", padx=5, pady=5)

        # Checkbox header (empty for alignment)
        ctk.CTkLabel(header_frame, text="", width=30).grid(row=0, column=0, padx=5, pady=5)

        # Preset Name header
        ctk.CTkLabel(header_frame, text="Preset Name", width=150, font=("Arial", 12, "bold")).grid(row=0, column=1, padx=5, pady=5)

        # Synth Type header
        ctk.CTkLabel(header_frame, text="Synth Type", width=100, font=("Arial", 12, "bold")).grid(row=0, column=2, padx=5, pady=5)

        # Created At header
        ctk.CTkLabel(header_frame, text="Created At", width=150, font=("Arial", 12, "bold")).grid(row=0, column=3, padx=5, pady=5)

        # Last Updated header
        ctk.CTkLabel(header_frame, text="Last Updated", width=150, font=("Arial", 12, "bold")).grid(row=0, column=4, padx=5, pady=5)

        # Get the presets sorted by the selected sort type
        presets = self.list_presets(self.sort_var.get())

        # Add presets to the UI
        for idx, (name, preset_type, created_at, last_updated) in enumerate(presets, start=1):
            frame = ctk.CTkFrame(self.preset_listbox)
            frame.pack(fill="x", padx=5, pady=2)

            # Add a checkbox for selecting the preset
            checkbox_var = ctk.BooleanVar(value=False)
            checkbox = ctk.CTkCheckBox(frame, text="", variable=checkbox_var, width=30)
            checkbox.grid(row=idx, column=0, padx=5, pady=5)

            # Store the checkbox variable for later use
            setattr(frame, "checkbox_var", checkbox_var)

            # Add the preset name
            ctk.CTkLabel(frame, text=name, width=150).grid(row=idx, column=1, padx=5, pady=5)

            # Add the synth type
            ctk.CTkLabel(frame, text=preset_type, width=100).grid(row=idx, column=2, padx=5, pady=5)

            # Add the created date
            ctk.CTkLabel(frame, text=created_at, width=150).grid(row=idx, column=3, padx=5, pady=5)

            # Add the last updated date
            ctk.CTkLabel(frame, text=last_updated, width=150).grid(row=idx, column=4, padx=5, pady=5)

            # Add Load and Delete buttons
            button_frame = ctk.CTkFrame(frame)
            button_frame.grid(row=idx, column=5, padx=5, pady=5)

            load_button = ctk.CTkButton(button_frame, text="Load", command=lambda n=name, t=preset_type: self.load_preset(n, t))
            load_button.pack(side="left", padx=2)

            delete_button = ctk.CTkButton(button_frame, text="Delete", command=lambda n=name: self.delete_preset(n))
            delete_button.pack(side="left", padx=2)

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
        selected_preset = None

        # Find the selected preset
        for widget in self.preset_listbox.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and hasattr(widget, "checkbox_var"):
                if widget.checkbox_var.get():  # Check if the checkbox is selected
                    # Extract the preset name and type from the labels in the frame
                    labels = [child for child in widget.winfo_children() if isinstance(child, ctk.CTkLabel)]
                    if len(labels) >= 4:  # Ensure there are at least four labels (name, type, created_at, last_updated)
                        preset_name = labels[0].cget("text")
                        preset_type = labels[1].cget("text")
                        selected_preset = (preset_name, preset_type)
                        break

        if not selected_preset:
            print("Error: No preset selected.")
            return

        preset_name, preset_type = selected_preset

        # Fetch the preset data
        preset_data = self.load_preset_data(preset_name, preset_type)
        if not preset_data:
            print("Error: Preset not found.")
            return

        # Prompt the user to choose a file path
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            # Export the preset
            PresetExporterImporter.export_preset(preset_data, file_path)
            print(f"Preset '{preset_name}' exported successfully to {file_path}")

    def import_preset(self):
        """Import a preset from a text file and load it into the appropriate synth."""
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            preset_data = PresetExporterImporter.import_preset(file_path)
            if preset_data:
                # Check if the preset data includes the synth type
                preset_type = preset_data.get("type")
                if preset_type not in ["Additive", "Subtractive"]:
                    print("Error: Invalid or missing synth type in imported preset.")
                    return

                # Navigate to the appropriate synth and load the preset
                self.app.navigate_to_synth(preset_type, preset_data)

                # Refresh the preset list after importing
                self.refresh_preset_list()
                        
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
    
    def preset_exists(self, preset_name, preset_type):
        """Check if a preset with the given name and type already exists."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            if preset_type == "Additive":
                cursor.execute("SELECT name FROM AdditivePresets WHERE user_id = ? AND name = ?", (self.user_id, preset_name))
            elif preset_type == "Subtractive":
                cursor.execute("SELECT name FROM SubtractivePresets WHERE user_id = ? AND name = ?", (self.user_id, preset_name))
            else:
                return False  # Invalid preset type

            result = cursor.fetchone()
            return result is not None  # Return True if the preset exists, False otherwise
        except sqlite3.Error as e:
            print(f"ERROR: Database error: {e}")
            return False
        finally:
            connection.close()