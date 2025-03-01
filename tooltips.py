import tkinter as tk

class Tooltip:
    """A reusable tooltip widget for providing additional context."""
    active_tooltip = None  # Track the currently active tooltip

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None

        # Bind events
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        """Display the tooltip."""
        if Tooltip.active_tooltip:
            Tooltip.active_tooltip.hide_tooltip(None)  # Hide the current tooltip

        # Calculate tooltip position
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        # Create tooltip window
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)  # Remove window decorations
        self.tooltip.wm_geometry(f"+{x}+{y}")

        # Add text to the tooltip
        self.label = tk.Label(
            self.tooltip,
            text=self.text,
            justify="left",
            background="lightyellow",
            relief="solid",
            borderwidth=1,
            font=("Arial", 10),
            fg="black",
        )
        self.label.pack(ipadx=5, ipady=5)

        Tooltip.active_tooltip = self  # Set this tooltip as active

    def hide_tooltip(self, event):
        """Hide the tooltip."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
            Tooltip.active_tooltip = None  # Clear the active tooltip

    def update_text(self, new_text):
        """Update the tooltip text dynamically."""
        self.text = new_text
        if self.tooltip:
            self.label.config(text=self.text)