import tkinter as tk

class Tooltip:
    """A reusable tooltip widget for providing additional context."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        print(f"Tooltip created for {widget}: {text}")  # Debug print
        self.tooltip = None

        # Bind events
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        """Display the tooltip."""
        if self.tooltip:
            return  # Tooltip already visible

        # Calculate tooltip position
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        # Create tooltip window
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)  # Remove window decorations
        self.tooltip.wm_geometry(f"+{x}+{y}")

        # Add text to the tooltip
        label = tk.Label(
            self.tooltip,
            text=self.text,  # Ensure this uses the correct tooltip text
            justify="left",
            background="lightyellow",  # Ensure the background contrasts the text
            relief="solid",
            borderwidth=1,
            font=("Arial", 10),
            fg="black",  # Set text color explicitly
        )
        label.pack(ipadx=5, ipady=5)

    def hide_tooltip(self, event):
        """Hide the tooltip."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

