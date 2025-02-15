import customtkinter as ctk
import sqlite3


from hash_encryption import HashEncryption

class LoginSystem:
    def __init__(self, parent, success_callback):
        self.parent = parent
        self.success_callback = success_callback
        self.current_user_id = None
        self.message_label = None  # Store reference to the message label
        self.create_login_ui()

        self.hash_encryptor = HashEncryption()

    def create_login_ui(self):
        self.clear_ui()

        self.username_entry = ctk.CTkEntry(self.parent, placeholder_text="Username")
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(self.parent, placeholder_text="Password", show="*")
        self.password_entry.pack(pady=10)

        self.login_button = ctk.CTkButton(self.parent, text="Login", command=self.authenticate)
        self.login_button.pack(pady=10)

        self.register_button = ctk.CTkButton(self.parent, text="Register", command=self.create_register_ui)
        self.register_button.pack(pady=10)

    def create_register_ui(self):
        """Create the registration UI."""
        self.clear_ui()

        self.username_entry = ctk.CTkEntry(self.parent, placeholder_text="Choose Username")
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(self.parent, placeholder_text="Choose Password", show="*")
        self.password_entry.pack(pady=10)

        self.register_button = ctk.CTkButton(self.parent, text="Register", command=self.register_user)
        self.register_button.pack(pady=10)

        self.back_button = ctk.CTkButton(self.parent, text="Back", command=self.create_login_ui)
        self.back_button.pack(pady=10)


    def authenticate(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            self.show_error("Please enter both username and password.")
            return

        with sqlite3.connect("synth.db") as connection:
            cursor = connection.cursor()

            query = "SELECT Uid, password, salt FROM Users WHERE username = ?"
            cursor.execute(query, (username,))
            result = cursor.fetchone()

        if result:
            user_id, stored_hash, salt = result
            if self.hash_encryptor.verify_password(password, salt, stored_hash):
                self.current_user_id = user_id
                self.success_callback(self.current_user_id)
            else:
                self.show_error("Invalid username or password.")
        else:
            self.show_error("Invalid username or password.")

    def clear_ui(self):
        """Remove all widgets from the parent frame."""
        for widget in self.parent.winfo_children():
            widget.destroy()

    def show_error(self, message):
        """Display an error message on the UI."""
        # Clear any existing messages
        if hasattr(self, "message_label") and self.message_label:
            self.message_label.destroy()

        # Create a new message label
        self.message_label = ctk.CTkLabel(self.parent, text=message, text_color="red")
        self.message_label.pack(pady=10)


    def register_user(self):
        """Register a new user."""
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            self.show_error("Username and password cannot be empty.")
            return

        # Hash the password for secure storage
        from hash_encryption import HashEncryption  # Assuming you are using custom hashing
        hash_encryptor = HashEncryption()

        salt, hashed_password = hash_encryptor.hash_password(password)

        try:
            # Insert the new user into the database
            with sqlite3.connect("synth.db") as connection:
                cursor = connection.cursor()
                query = "INSERT INTO Users (username, password, salt) VALUES (?, ?, ?)"
                cursor.execute(query, (username, hashed_password, salt))
                connection.commit()

            self.show_message("Registration successful! Please log in.")
            self.create_login_ui()
        except sqlite3.IntegrityError:
            self.show_error("Username already exists. Please choose another.")


    def show_error(self, message):
        self._update_message(message, "red")

    def show_message(self, message):
        self._update_message(message, "green")

    def _update_message(self, message, color):
        """Display a single message at a time."""
        if self.message_label:
            self.message_label.destroy()
        self.message_label = ctk.CTkLabel(self.parent, text=message, text_color=color)
        self.message_label.pack(pady=10)

    def clear_ui(self):
        """Clear all widgets from the parent frame."""
        for widget in self.parent.winfo_children():
            widget.destroy()
        self.message_label = None
