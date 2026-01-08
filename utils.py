# utils.py
import ctypes
import customtkinter as ctk
import tkinter as tk

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def format_size(s):
    if s < 1024: return f"{s} B"
    if s < 1024**2: return f"{s/1024:.1f} KB"
    return f"{s/1024**2:.1f} MB"

def add_info_section(parent, title, info_text):
    frame = ctk.CTkFrame(parent, fg_color="gray20", corner_radius=10)
    frame.pack(fill="x", padx=20, pady=(10, 20))
    header = ctk.CTkFrame(frame, fg_color="transparent")
    header.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
    info_label = ctk.CTkLabel(frame, text=info_text, text_color="gray", anchor="w", justify="left")
    info_label.pack(fill="x", padx=10, pady=(0,10), anchor="w")
    return frame

def create_meter(parent, title):
    frame = ctk.CTkFrame(parent)
    frame.pack(fill="x", pady=10, padx=10)
    ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
    bar = ctk.CTkProgressBar(frame)
    bar.pack(fill="x", padx=10, pady=5)
    label = ctk.CTkLabel(frame, text="0%")
    label.pack(pady=5)
    return bar, label

def create_history_chart(parent, title):
    outer_frame = ctk.CTkFrame(parent)
    outer_frame.pack(fill="x", pady=5, padx=10)
    header = ctk.CTkFrame(outer_frame)
    header.pack(fill="x", padx=5, pady=5)
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
    current_val_lbl = ctk.CTkLabel(header, text="0%", width=50, anchor="e")
    current_val_lbl.pack(side="right", padx=5)
    chart_frame = ctk.CTkFrame(outer_frame, fg_color="gray20")
    chart_frame.pack(fill="x", padx=5, pady=5)
    
    # Simple Axis
    axis = ctk.CTkFrame(chart_frame, fg_color="gray30", width=30)
    axis.pack(side="right", fill="y")
    ctk.CTkLabel(axis, text="100%", font=ctk.CTkFont(size=8)).pack()
    ctk.CTkLabel(axis, text="50%", font=ctk.CTkFont(size=8)).pack(expand=True)
    ctk.CTkLabel(axis, text="0%", font=ctk.CTkFont(size=8)).pack(side="bottom")
    
    canvas = tk.Canvas(chart_frame, bg="gray20", highlightthickness=0, height=150)
    canvas.pack(side="left", fill="both", expand=True)
    return (outer_frame, canvas, current_val_lbl)

def draw_line_chart(canvas, data, color):
    try:
        canvas.update()
        w = canvas.winfo_width()
        h = int(canvas['height'])
    except:
        return
    
    if w < 10: w = 600
    canvas.delete("all")
    
    # Grid lines
    for pct in [0.25, 0.5, 0.75]:
        y = h - (pct * h)
        canvas.create_line(0, y, w, y, fill="gray25", dash=(2, 2))
        
    if len(data) < 2: return
    
    step_x = w / (len(data) - 1)
    points = []
    for i, val in enumerate(data):
        x = i * step_x
        y = h - (val / 100 * h)
        points.append(x)
        points.append(y)
        
    canvas.create_line(points, fill=color, width=2, smooth=True)

def create_dynamic_chart(parent, title):
    # Similar to history chart but meant for non-percentage data (traffic)
    outer_frame = ctk.CTkFrame(parent)
    outer_frame.pack(fill="x", pady=5, padx=10)
    
    header = ctk.CTkFrame(outer_frame)
    header.pack(fill="x", padx=5, pady=5)
    ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
    
    max_lbl = ctk.CTkLabel(header, text="Max: 0 KB/s", width=100, anchor="e")
    max_lbl.pack(side="right", padx=5)
    
    chart_frame = ctk.CTkFrame(outer_frame, fg_color="gray20")
    chart_frame.pack(fill="x", padx=5, pady=5)
    
    canvas = tk.Canvas(chart_frame, bg="gray20", highlightthickness=0, height=100)
    canvas.pack(fill="both", expand=True)
    
    return outer_frame, canvas, max_lbl