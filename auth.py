import sqlite3
import hashlib
import customtkinter as ctk

DATABASE = 'synth.db'


class AuthApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sound Synthesis")
        self.geometry("600x400")
        self.resizable(False, False)

        # Default frame (Login)
        self.current_frame = None
        self.show_login_page()

    def show_login_page(self):
        if self.current_frame:
            self.current_frame.destroy()

        self.current_frame = ctk.CTkFrame(self)
        self.current_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.current_frame, text="Login", font=("Arial", 20)).pack(pady=10)

        # Username Entry
        ctk.CTkLabel(self.current_frame, text="Username:").pack(pady=5)
        self.username_entry = ctk.CTkEntry(self.current_frame)
        self.username_entry.pack(pady=5)

        # Password Entry
        ctk.CTkLabel(self.current_frame, text="Password:").pack(pady=5)
        self.password_entry = ctk.CTkEntry(self.current_frame, show="*")
        self.password_entry.pack(pady=5)

        # Login Button
        ctk.CTkButton(self.current_frame, text="Log In", command=self.login_user).pack(pady=10)

        # Go to Register Button
        ctk.CTkButton(self.current_frame, text="Register", command=self.show_register_page).pack(pady=5)

    def show_register_page(self):
        if self.current_frame:
            self.current_frame.destroy()

        self.current_frame = ctk.CTkFrame(self)
        self.current_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.current_frame, text="Register", font=("Arial", 20)).pack(pady=10)

        # Username Entry
        ctk.CTkLabel(self.current_frame, text="Username:").pack(pady=5)
        self.username_entry = ctk.CTkEntry(self.current_frame)
        self.username_entry.pack(pady=5)

        # Password Entry
        ctk.CTkLabel(self.current_frame, text="Password:").pack(pady=5)
        self.password_entry = ctk.CTkEntry(self.current_frame, show="*")
        self.password_entry.pack(pady=5)

        # Confirm Password Entry
        ctk.CTkLabel(self.current_frame, text="Confirm Password:").pack(pady=5)
        self.confirm_password_entry = ctk.CTkEntry(self.current_frame, show="*")
        self.confirm_password_entry.pack(pady=5)

        # Register Button
        ctk.CTkButton(self.current_frame, text="Register", command=self.register_user).pack(pady=10)

        # Back to Login Button
        ctk.CTkButton(self.current_frame, text="Back to Login", command=self.show_login_page).pack(pady=5)

    def login_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
        user = cursor.fetchone()
        connection.close()

        if user:
            self.start_main_app(user[0])
        else:
            ctk.CTkLabel(self.current_frame, text="Invalid credentials!", fg_color="red").pack(pady=5)

    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()

        if password != confirm_password:
            ctk.CTkLabel(self.current_frame, text="Passwords do not match!", fg_color="red").pack(pady=5)
            return

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            connection.commit()
            ctk.CTkLabel(self.current_frame, text="Registration successful! Please log in.", fg_color="green").pack(pady=5)
        except sqlite3.IntegrityError:
            ctk.CTkLabel(self.current_frame, text="Username already exists!", fg_color="red").pack(pady=5)
        finally:
            connection.close()

    def start_main_app(self, user_id):
        """
        Start the main synthesizer app with the logged-in user's ID.
        """
        # Delayed import to avoid circular dependency
        from main import SynthApp

        self.destroy()  # Close the auth window
        app = SynthApp(user_id=user_id)  # Pass user_id to SynthApp
        app.mainloop()


if __name__ == "__main__":
    auth_app = AuthApp()
    auth_app.mainloop()
