import sqlite3
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
from utils import MergeSort, PresetExporterImporter
import scipy.io.wavfile as wavfile
from utils import ScrollableFrame


class PresetManager:
    def __init__(self, Uid, parent, app, db_path="synth.db"):
        self.db_path = db_path
        self.Uid = Uid
        self.parent = parent  # Presets tab (UI parent)
        self.app = app  # Reference to the main SynthApp
        self.selected_preset_var = ctk.StringVar(value="")  # Track the selected preset
        self.create_preset_ui()
        
                
    def save_preset(self, preset_name, preset_type, preset_data):
        """Save or update a preset in the database."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Check if the preset already exists
            if preset_type == "Additive":
                cursor.execute("SELECT name FROM AdditivePresets WHERE Uid = ? AND name = ?", (self.Uid, preset_name))
            elif preset_type == "Subtractive":
                cursor.execute("SELECT name FROM SubtractivePresets WHERE Uid = ? AND name = ?", (self.Uid, preset_name))

            preset_exists = cursor.fetchone() is not None

            if preset_type == "Additive":
                if preset_exists:
                    # Update existing preset
                    cursor.execute("""
                        UPDATE AdditivePresets
                        SET base_frequency = ?, sample_rate = ?, duration = ?, volume = ?, tone = ?, num_harmonics = ?, attack = ?, decay = ?, sustain = ?, release = ?, last_updated = ?
                        WHERE Uid = ? AND name = ?
                    """, (
                        preset_data["base_frequency"], preset_data["sample_rate"], preset_data["duration"],
                        preset_data["volume"], preset_data["tone"], preset_data["num_harmonics"], preset_data["adsr"]["attack"],
                        preset_data["adsr"]["decay"], preset_data["adsr"]["sustain"], preset_data["adsr"]["release"], current_time,
                        self.Uid, preset_name
                    ))
                else:
                    # Insert new preset
                    cursor.execute("""
                        INSERT INTO AdditivePresets (Uid, name, base_frequency, sample_rate, duration, volume, tone, num_harmonics, attack, decay, sustain, release, created_at, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.Uid, preset_name, preset_data["base_frequency"], preset_data["sample_rate"], preset_data["duration"],
                        preset_data["volume"], preset_data["tone"], preset_data["num_harmonics"], preset_data["adsr"]["attack"],
                        preset_data["adsr"]["decay"], preset_data["adsr"]["sustain"], preset_data["adsr"]["release"], current_time, current_time
                    ))

            elif preset_type == "Subtractive":
                if preset_exists:
                    # Update existing preset
                    cursor.execute("""
                        UPDATE SubtractivePresets
                        SET volume = ?, last_updated = ?
                        WHERE Uid = ? AND name = ?
                    """, (preset_data["volume"], current_time, self.Uid, preset_name))

                    # Get the preset ID
                    cursor.execute("SELECT Sid FROM SubtractivePresets WHERE Uid = ? AND name = ?", (self.Uid, preset_name))
                    Sid = cursor.fetchone()[0]

                    # Delete existing components (oscillators, filters, effects, LFOs)
                    cursor.execute("DELETE FROM SubtractivePresetOscillators WHERE Sid = ?", (Sid,))
                    cursor.execute("DELETE FROM SubtractivePresetFilters WHERE Sid = ?", (Sid,))
                    cursor.execute("DELETE FROM SubtractivePresetEffects WHERE Sid = ?", (Sid,))
                    cursor.execute("DELETE FROM SubtractivePresetLFOs WHERE Sid = ?", (Sid,))

                    # Save updated components
                    self.save_subtractive_components(cursor, Sid, preset_data)
                else:
                    # Insert new preset
                    cursor.execute("""
                        INSERT INTO SubtractivePresets (Uid, name, volume, created_at, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (self.Uid, preset_name, preset_data["volume"], current_time, current_time))

                    # Get the ID of the newly created preset
                    Sid = cursor.lastrowid

                    # Save oscillators, filters, effects, and LFOs
                    self.save_subtractive_components(cursor, Sid, preset_data)

            connection.commit()
            print(f"Preset '{preset_name}' {'updated' if preset_exists else 'saved'} successfully!")
        except sqlite3.Error as e:
            print(f"ERROR: Database error: {e}")
        finally:
            connection.close()

        # Refresh the preset list after saving
        self.refresh_preset_list()



    def save_subtractive_components(self, cursor, Sid, preset_data):
        """Save the oscillators, filters, effects, and LFOs for a subtractive synthesizer preset."""
        # Save oscillators
        for osc in preset_data.get("oscillators", []):
            cursor.execute("""
                INSERT INTO SubtractivePresetOscillators (Sid, type, frequency, amplitude)
                VALUES (?, ?, ?, ?)
            """, (Sid, osc["type"], osc["frequency"], osc["amplitude"]))

        # Save filters
        for filt in preset_data.get("filters", []):
            cursor.execute("""
                INSERT INTO SubtractivePresetFilters (Sid, filter_type, cutoff_frequency, resonance)
                VALUES (?, ?, ?, ?)
            """, (Sid, filt["type"], filt["cutoff"], filt["resonance"]))

        # Save effects
        for effect in preset_data.get("effects", []):
            # Insert the effect into the Effects table if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO Effects (name)
                VALUES (?)
            """, (effect["type"],))

            # Get the effect ID
            cursor.execute("SELECT Eid FROM Effects WHERE name = ?", (effect["type"],))
            Eid = cursor.fetchone()[0]

            # Save the effect parameters
            cursor.execute("""
                INSERT INTO SubtractivePresetEffects (Sid, Eid, parameters)
                VALUES (?, ?, ?)
            """, (Sid, Eid, json.dumps(effect["params"])))

        # Save LFOs
        for lfo in preset_data.get("lfos", []):
            cursor.execute("""
                INSERT INTO SubtractivePresetLFOs (Sid, shape, frequency, depth, target)
                VALUES (?, ?, ?, ?, ?)
            """, (Sid, lfo["shape"], lfo["frequency"], lfo["depth"], lfo["target"]))             
    def list_presets(self, sort_by="name"):
        """Retrieve a sorted list of all presets for the user."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        # Retrieve additive presets
        cursor.execute("""
            SELECT name, 'Additive' as type, created_at, last_updated
            FROM AdditivePresets
            WHERE Uid = ?
        """, (self.Uid,))
        additive_presets = cursor.fetchall()

        # Retrieve subtractive presets
        cursor.execute("""
            SELECT name, 'Subtractive' as type, created_at, last_updated
            FROM SubtractivePresets
            WHERE Uid = ?
        """, (self.Uid,))
        subtractive_presets = cursor.fetchall()

        # Combine the results
        presets = additive_presets + subtractive_presets

        connection.close()

        # Sort the presets based on the selected sort type using MergeSort
        if sort_by == "name":
            presets = MergeSort.sort(presets, key=lambda x: x[0])  # Sort by name (ascending)
        elif sort_by == "created_at":
            presets = MergeSort.sort(presets, key=lambda x: x[2], reverse=True)  # Sort by creation date (latest first)
        elif sort_by == "last_updated":
            presets = MergeSort.sort(presets, key=lambda x: x[3], reverse=True)  # Sort by last updated date (latest first)

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
            cursor.execute("DELETE FROM AdditivePresets WHERE Uid = ? AND name = ?", (self.Uid, preset_name))
            
            # Delete from SubtractivePresets
            cursor.execute("DELETE FROM SubtractivePresets WHERE Uid = ? AND name = ?", (self.Uid, preset_name))
            
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
        # Sort menu and scrollable frame (existing code)
        self.sort_var = ctk.StringVar(value="name")
        ctk.CTkLabel(self.parent, text="Sort by:").pack(pady=5)
        self.sort_menu = ctk.CTkComboBox(self.parent, values=["name", "created_at", "last_updated"], variable=self.sort_var, command=self.refresh_preset_list)
        self.sort_menu.pack(pady=5)

        self.scrollable_preset_frame = ScrollableFrame(self.parent, width=450, height=300)
        self.scrollable_preset_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Add the preset listbox inside the scrollable frame
        self.preset_listbox = ctk.CTkFrame(self.scrollable_preset_frame)
        self.preset_listbox.pack(fill="both", expand=True)

        # Add Import/Export/Save as WAV buttons (existing code)
        button_frame = ctk.CTkFrame(self.parent)
        button_frame.pack(fill="x", padx=10, pady=10)

        export_button = ctk.CTkButton(button_frame, text="Export Preset", command=self.export_preset)
        export_button.pack(side="left", padx=5)

        import_button = ctk.CTkButton(button_frame, text="Import Preset", command=self.import_preset)
        import_button.pack(side="left", padx=5)

        save_wav_button = ctk.CTkButton(button_frame, text="Save as .WAV", command=self.save_as_wav)
        save_wav_button.pack(side="left", padx=5)

        # Add Upload to Community Library button
        upload_button = ctk.CTkButton(button_frame, text="Upload to Community Library", command=self.upload_to_community_library)
        upload_button.pack(side="left", padx=5)

        self.refresh_preset_list()

    def upload_to_community_library(self):
        """Upload the selected preset to the community library."""
        selected_preset_name = self.selected_preset_var.get()
        if not selected_preset_name:
            messagebox.showerror("Error", "No preset selected.")
            return

        # Get the preset type (Additive or Subtractive)
        preset_type = self.get_preset_type(selected_preset_name)
        if not preset_type:
            messagebox.showerror("Error", "Preset not found.")
            return

        # Fetch the preset data
        preset_data = self.load_preset_data(selected_preset_name, preset_type)
        if not preset_data:
            messagebox.showerror("Error", "Failed to load preset data.")
            return

        # Upload the preset to the community library
        self.app.community_preset_manager.save_preset_to_community(preset_data["name"], preset_type, preset_data)

    def refresh_preset_list(self, *args):
        """Refresh the preset list inside the UI with headers and radio buttons for single selection."""
        # Clear existing widgets in the preset listbox
        for widget in self.preset_listbox.winfo_children():
            widget.destroy()

        # Add headers
        header_frame = ctk.CTkFrame(self.preset_listbox)
        header_frame.pack(fill="x", padx=5, pady=5)

        # Column headers
        headers = ["", "Preset Name", "Synth Type", "Created At", "Last Updated", "Actions"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(header_frame, text=header, font=("Arial", 12, "bold")).grid(row=0, column=col, padx=50, pady=5)

        # Get the presets sorted by the selected sort type
        presets = self.list_presets(self.sort_var.get())

        # Use a single StringVar to track the selected preset
        self.selected_preset_var = ctk.StringVar(value="")

        # Add presets to the UI
        for idx, (name, preset_type, created_at, last_updated) in enumerate(presets, start=1):
            frame = ctk.CTkFrame(self.preset_listbox)
            frame.pack(fill="x", padx=5, pady=2)

            # Add a radio button for selecting the preset
            radio_button = ctk.CTkRadioButton(
                frame,
                text="",
                variable=self.selected_preset_var,
                value=name,  # Use the preset name as the value
            )
            radio_button.grid(row=idx, column=0, padx=5, pady=5)

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
                WHERE Uid = ? AND name = ?
            """, (self.Uid, preset_name))
            result = cursor.fetchone()

            if not result:
                print(f"Error: Additive Preset '{preset_name}' not found.")
                return None

            # Extract the data
            base_frequency, sample_rate, duration, volume, tone, num_harmonics, attack, decay, sustain, release = result

            return {
                "type": preset_type,
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
                WHERE Uid = ? AND name = ?
            """, (self.Uid, preset_name))
            preset = cursor.fetchone()
            
            if not preset:
                print(f"Error: Subtractive Preset '{preset_name}' not found.")
                return None
            
            Sid, volume = preset

            # Retrieve filters
            cursor.execute("""
                SELECT filter_type, cutoff_frequency, resonance FROM SubtractivePresetFilters 
                WHERE Sid = ?
            """, (Sid,))
            filters = [{"type": row[0], "cutoff": row[1], "resonance": row[2]} for row in cursor.fetchall()]

            # Retrieve oscillators
            cursor.execute("""
                SELECT type, frequency, amplitude FROM SubtractivePresetOscillators 
                WHERE Sid = ?
            """, (Sid,))
            oscillators = [{"type": row[0], "frequency": row[1], "amplitude": row[2]} for row in cursor.fetchall()]

            # Retrieve effects
            cursor.execute("""
                SELECT e.name, spe.parameters FROM SubtractivePresetEffects spe
                JOIN Effects e ON spe.Eid = e.Eid
                WHERE spe.Sid = ?
            """, (Sid,))
            effects = [{"type": row[0], "params": json.loads(row[1])} for row in cursor.fetchall()]

            # Retrieve LFOs (fix: ensure correct SQL column names)
            cursor.execute("""
                SELECT shape, frequency, depth, target FROM SubtractivePresetLFOs
                WHERE Sid = ?
            """, (Sid,))
            lfos = [{"shape": row[0], "frequency": row[1], "depth": row[2], "target": row[3]} for row in cursor.fetchall()]

            return {
                "type": preset_type,
                "name": preset_name,
                "volume": volume,
                "oscillators": oscillators,
                "filters": filters,
                "effects": effects,
                "lfos": lfos  # Fix: Ensure LFOs are retrieved
            }
            
    def export_preset(self):
        """Export the selected preset to a text file."""
        selected_preset_name = self.selected_preset_var.get()
        if not selected_preset_name:
            print("Error: No preset selected.")
            return

        # Find the preset type (Additive or Subtractive)
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("SELECT 'Additive' FROM AdditivePresets WHERE Uid = ? AND name = ?", (self.Uid, selected_preset_name))
        if cursor.fetchone():
            preset_type = "Additive"
        else:
            cursor.execute("SELECT 'Subtractive' FROM SubtractivePresets WHERE Uid = ? AND name = ?", (self.Uid, selected_preset_name))
            if cursor.fetchone():
                preset_type = "Subtractive"
            else:
                print("Error: Preset not found.")
                return

        connection.close()

        # Fetch the preset data
        preset_data = self.load_preset_data(selected_preset_name, preset_type)
        if not preset_data:
            print("Error: Preset not found.")
            return

        # Prompt the user to choose a file path
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            # Export the preset
            PresetExporterImporter.export_preset(preset_data, file_path)
            print(f"Preset '{selected_preset_name}' exported successfully to {file_path}")
    def import_preset(self):
        """Import a preset from a text file and load it into the appropriate synth."""
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            preset_data = PresetExporterImporter.import_preset(file_path)
            if preset_data:
                print(f"Imported Preset Data: {preset_data}")  # Debug statement
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

        cursor.execute("SELECT 'Additive' FROM AdditivePresets WHERE name = ? AND Uid = ?", (preset_name, self.Uid))
        if cursor.fetchone():
            connection.close()
            return "Additive"

        cursor.execute("SELECT 'Subtractive' FROM SubtractivePresets WHERE name = ? AND Uid = ?", (preset_name, self.Uid))
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
                cursor.execute("SELECT name FROM AdditivePresets WHERE Uid = ? AND name = ?", (self.Uid, preset_name))
            elif preset_type == "Subtractive":
                cursor.execute("SELECT name FROM SubtractivePresets WHERE Uid = ? AND name = ?", (self.Uid, preset_name))
            else:
                return False  # Invalid preset type

            result = cursor.fetchone()
            return result is not None  # Return True if the preset exists, False otherwise
        except sqlite3.Error as e:
            print(f"ERROR: Database error: {e}")
            return False
        finally:
            connection.close()

    def upload_preset_to_community(self):
        """Upload the current preset to the community library."""
        current_tab = self.app.tab_view.get()
        if current_tab == "Additive Synth":
            preset_data = self.app.additive_synth.get_preset_data("Community Preset")
            preset_type = "Additive"
        elif current_tab == "Subtractive Synth":
            preset_data = self.app.subtractive_synth.get_preset_data("Community Preset")
            preset_type = "Subtractive"
        else:
            messagebox.showerror("Error", "No active synth tab.")
            return

        # Use the CommunityPresetManager to upload the preset
        self.app.community_preset_manager.save_preset_to_community(preset_data["name"], preset_type, preset_data)

            
    def save_as_wav(self):
        """Save the selected preset's waveform as a .WAV file."""
        selected_preset_name = self.selected_preset_var.get()
        if not selected_preset_name:
            print("Error: No preset selected.")
            return

        # Get the preset type (Additive or Subtractive)
        preset_type = self.get_preset_type(selected_preset_name)
        if not preset_type:
            print("Error: Preset not found.")
            return

        # Fetch the preset data
        preset_data = self.load_preset_data(selected_preset_name, preset_type)
        if not preset_data:
            print("Error: Preset not found.")
            return

        # Generate the waveform
        if preset_type == "Additive":
            waveform = self.app.additive_synth.generate_waveform()
        elif preset_type == "Subtractive":
            waveform = self.app.subtractive_synth.generate_waveform()
        else:
            print("Error: Unknown preset type.")
            return

        # Prompt the user to choose a file path
        file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Files", "*.wav")])
        if file_path:
            # Save the waveform as a .WAV file
            wavfile.write(file_path, self.app.sample_rate, waveform)
            print(f"Waveform saved as {file_path}")

import sqlite3
import json
import customtkinter as ctk
from tkinter import messagebox
from utils import ScrollableFrame

class CommunityPresetManager:
    def __init__(self, parent, Uid, app, db_path="synth.db"):
        self.parent = parent
        self.Uid = Uid
        self.app = app
        self.db_path = db_path

        self.check_community_presets_table()

        # Initialize the UI
        self.create_ui()

    def create_ui(self):
        """Create the UI for the community presets tab."""
        self.community_presets_frame = ctk.CTkFrame(self.parent)
        self.community_presets_frame.pack(fill="both", expand=True)

        # Add a scrollable frame for the community presets list
        self.scrollable_community_frame = ScrollableFrame(self.community_presets_frame, width=450, height=300)
        self.scrollable_community_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Refresh the list of community presets
        self.refresh_community_presets_list()

    def refresh_community_presets_list(self):
        """Refresh the list of community presets in the UI."""
        for widget in self.scrollable_community_frame.winfo_children():
            widget.destroy()

        presets = self.list_community_presets()
        if not presets:
            # Display a message if no presets are found
            ctk.CTkLabel(self.scrollable_community_frame, text="No presets found in the community library.").pack(pady=10)
            return

        # Add headers
        headers = ["Preset Name", "Type", "Creator", "Created At", ""]
        header_frame = ctk.CTkFrame(self.scrollable_community_frame)
        header_frame.pack(fill="x", pady=5)
        
        for col, header in enumerate(headers):
            ctk.CTkLabel(header_frame, text=header, font=("Arial", 12, "bold")).grid(
                row=0, column=col, padx=5, pady=5)

        # Add presets
        presets = self.list_community_presets()
        for idx, (cid, name, ptype, created_at, username) in enumerate(presets, 1):
            frame = ctk.CTkFrame(self.scrollable_community_frame)
            frame.pack(fill="x", padx=5, pady=2)

            # Display information
            ctk.CTkLabel(frame, text=name).grid(row=idx, column=0, padx=50, pady=5)
            ctk.CTkLabel(frame, text=ptype).grid(row=idx, column=1, padx=50, pady=5)
            ctk.CTkLabel(frame, text=username).grid(row=idx, column=2, padx=50, pady=5)
            ctk.CTkLabel(frame, text=created_at).grid(row=idx, column=3, padx=50, pady=5)

            # Load button
            load_btn = ctk.CTkButton(
                frame, 
                text="Load",
                command=lambda cid=cid: self.load_preset_from_community(cid)
            )
            load_btn.grid(row=idx, column=4, padx=5, pady=5)
    def load_selected_preset(self):
        """Load the selected community preset into the appropriate synth."""
        selected_Sid = self.get_selected_Sid()
        if not selected_Sid:
            messagebox.showerror("Error", "No preset selected.")
            return

        self.load_preset_from_community(selected_Sid)

    def get_selected_Sid(self):
        """Get the ID of the selected community preset."""
        # This method should return the ID of the selected preset in the UI.
        # You can implement this based on how the selection is tracked in your UI.
        # For now, we assume the first preset is selected.
        presets = self.list_community_presets()
        if presets:
            return presets[0][0]  # Return the ID of the first preset
        return None

    def load_preset_from_community(self, Sid):
        """Load a preset from the community library into the appropriate synth."""
        preset_data = self.load_preset_data(Sid)
        if preset_data:
            self.app.navigate_to_synth(preset_data["type"], preset_data)

    def load_preset_data(self, Sid):
        """Load a preset from the community library."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            # Fetch the preset data from the community library
            cursor.execute("SELECT preset_type, preset_data FROM CommunityPresets WHERE Cid = ?", (Sid,))
            result = cursor.fetchone()
            if not result:
                messagebox.showerror("Error", "Preset not found in the community library.")
                return None

            preset_type, preset_data_json = result
            preset_data = json.loads(preset_data_json)

            messagebox.showinfo("Success", f"Preset '{preset_data['name']}' loaded successfully!")
            return preset_data
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"ERROR: Database error: {e}")
            return None
        finally:
            connection.close()
    def check_community_presets_table(self):
        """Debugging function to check if the CommunityPresets table exists and contains data."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            # Check if the table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='CommunityPresets'")
            table_exists = cursor.fetchone()
            if not table_exists:
                print("Error: CommunityPresets table does not exist.")
                return

            # Check if the table contains data
            cursor.execute("SELECT * FROM CommunityPresets")
            presets = cursor.fetchall()
            if not presets:
                print("Warning: CommunityPresets table is empty.")
            else:
                print("Community Presets:")
                for preset in presets:
                    print(preset)
        except sqlite3.Error as e:
            print(f"ERROR: Database error: {e}")
        finally:
            connection.close()

    def save_preset_to_community(self, preset_name, preset_type, preset_data):
        """Save a preset to the community library."""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        try:
            # Check if the preset already exists in the community library
            cursor.execute("SELECT name FROM CommunityPresets WHERE name = ? AND preset_type = ?", (preset_name, preset_type))
            if cursor.fetchone():
                messagebox.showerror("Error", "A preset with this name already exists in the community library.")
                return

            # Insert the preset into the community library
            cursor.execute("""
                INSERT INTO CommunityPresets (Uid, name, preset_type, preset_data)
                VALUES (?, ?, ?, ?)
            """, (self.Uid, preset_name, preset_type, json.dumps(preset_data)))

            connection.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"ERROR: Database error: {e}")
        finally:
            connection.close()
        # Refresh immediately after successful upload
        self.app.after(0, self.refresh_community_presets_list)
        self.app.after(0, lambda: messagebox.showinfo("Success", "Preset uploaded successfully!"))

    def list_community_presets(self):
        """Retrieve list with usernames"""
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            cursor.execute("""
                SELECT cp.Cid, cp.name, cp.preset_type, cp.created_at, u.username 
                FROM CommunityPresets cp
                JOIN Users u ON cp.Uid = u.Uid
                ORDER BY cp.created_at DESC
            """)
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            if 'connection' in locals():
                connection.close()


