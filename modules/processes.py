import customtkinter as ctk
import psutil
from utils import add_info_section, is_admin

class ProcessesModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Process Priority", "Force Windows to prioritize specific applications.")
        
        # Warning label
        ctk.CTkLabel(self.frame, text="⚠️ Warning: Don't set everything to High.", text_color="red").pack()
        
        self.proc_list = ctk.CTkScrollableFrame(self.frame)
        self.proc_list.pack(fill="both", expand=True, padx=20, pady=10)
        self.load_processes()

    def load_processes(self):
        # psutil logic to list processes
        pass