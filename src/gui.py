import customtkinter as ctk
from customtkinter import filedialog
import threading
import time
from relic_processor import run_scanner

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("GFL2 Relic Scanner")
        self.geometry("600x650")
        self._cancel_event = None

        # Layout
        self.grid_columnconfigure(1, weight=1)

        # Output Path
        self.output_label = ctk.CTkLabel(self, text="Output File:")
        self.output_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.output_entry = ctk.CTkEntry(self)
        self.output_entry.insert(0, "inventory.json")
        self.output_entry.grid(row=0, column=1, padx=(0, 10), pady=(20, 10), sticky="ew")
        
        self.output_btn = ctk.CTkButton(self, text="Browse", command=self.browse_file, width=80)
        self.output_btn.grid(row=0, column=2, padx=(0, 20), pady=(20, 10))

        # Start Delay Configuration
        self.delay_label = ctk.CTkLabel(self, text="Start Delay (s):")
        self.delay_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.delay_entry = ctk.CTkEntry(self)
        self.delay_entry.insert(0, "2.0")
        self.delay_entry.grid(row=1, column=1, columnspan=2, padx=20, pady=10, sticky="ew")
        
        # Speed Configuration
        self.speed_label = ctk.CTkLabel(self, text="Scan Delay (s):")
        self.speed_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.speed_entry = ctk.CTkEntry(self)
        self.speed_entry.insert(0, "0.27")
        self.speed_entry.grid(row=2, column=1, columnspan=2, padx=20, pady=10, sticky="ew")
        
        # Max Relics Limit
        self.num_label = ctk.CTkLabel(self, text="Max Relics (Blank=All):")
        self.num_label.grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.num_entry = ctk.CTkEntry(self)
        self.num_entry.grid(row=3, column=1, columnspan=2, padx=20, pady=10, sticky="ew")

        # Category Dropdown
        self.cat_label = ctk.CTkLabel(self, text="Category:")
        self.cat_label.grid(row=4, column=0, padx=20, pady=10, sticky="w")
        self.cat_optionmenu = ctk.CTkOptionMenu(self, values=["All", "bulwark", "sentinel", "support", "vanguard"])
        self.cat_optionmenu.grid(row=4, column=1, columnspan=2, padx=20, pady=10, sticky="ew")

        # Log Text Box
        self.log_textbox = ctk.CTkTextbox(self, height=200)
        self.log_textbox.grid(row=5, column=0, columnspan=3, padx=20, pady=10, sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Progress Bar
        self.progressbar = ctk.CTkProgressBar(self)
        self.progressbar.grid(row=6, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.progressbar.set(0)

        # Start / Stop Buttons
        self.start_btn = ctk.CTkButton(self, text="Start Scan", command=self.start_scan)
        self.start_btn.grid(row=7, column=0, columnspan=2, padx=(20, 5), pady=(10, 20), sticky="ew")

        self.stop_btn = ctk.CTkButton(self, text="Stop (F8)", fg_color="#c0392b", hover_color="#96281b", command=self.cancel_scan, state="disabled")
        self.stop_btn.grid(row=7, column=2, padx=(5, 20), pady=(10, 20), sticky="ew")

    def browse_file(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, filename)

    def log_message(self, message):
        # Must schedule GUI updates from the main thread
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def update_progress(self, current, total):
        self.after(0, self._set_progress, current, total)
        
    def _set_progress(self, current, total):
        if total > 0:
            self.progressbar.set(current / total)

    def scan_complete(self, total_processed, output_path, cancelled=False):
        self.after(0, self._scan_complete, total_processed, output_path, cancelled)
        
    def _scan_complete(self, total_processed, output_path, cancelled=False):
        self.start_btn.configure(state="normal", text="Start Scan")
        self.stop_btn.configure(state="disabled")
        self._cancel_event = None
        if cancelled:
            self.log_message(f"=== Scan Cancelled ===")
            self.log_message(f"Partial results ({total_processed} items) saved to {output_path}")
        else:
            self.log_message(f"=== Scan Complete! ===")
            self.log_message(f"Saved {total_processed} items to {output_path}")

    def cancel_scan(self):
        if self._cancel_event:
            self._cancel_event.set()
            self.log_message("Cancelling... waiting for OCR to finish current item.")
            self.stop_btn.configure(state="disabled")

    def start_scan(self):
        # Disable start button, enable stop
        self.start_btn.configure(state="disabled", text="Scanning...")
        self.stop_btn.configure(state="normal")
        self.progressbar.set(0)
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        # Create a fresh cancel event for this run
        self._cancel_event = threading.Event()

        # Read configs
        cat_val = self.cat_optionmenu.get()
        parsed_cat = cat_val if cat_val != "All" else None
        
        num_val = self.num_entry.get()
        parsed_num = int(num_val) if num_val.strip() else None

        delay_val = float(self.delay_entry.get() or "2.0")
        speed_val = float(self.speed_entry.get() or "0.27")
        out_val = self.output_entry.get()

        config = {
            "type": parsed_cat,
            "num": parsed_num,
            "delay": delay_val,
            "speed": speed_val,
            "output": out_val
        }

        # Run scanner in separate thread to keep UI responsive
        threading.Thread(
            target=run_scanner,
            args=(config, self.log_message, self.update_progress, self.scan_complete, self._cancel_event),
            daemon=True
        ).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
