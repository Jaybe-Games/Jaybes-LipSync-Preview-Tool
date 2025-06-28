import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import os
import threading
import numpy as np
import soundfile as sf
import sounddevice as sd
import time
import math
import json

CONFIG_FILE = 'liptool_config.json'

class LipsyncGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Jaybe's Lipsync Preview Tool")
        self.root.geometry("1920x1080")

        # Dark mode is default
        self.dark_mode = True

        self.audio_dir = ""
        self.audio_files = []
        self.selected_audio = None
        self.sprites = [None, None, None]
        self.sprite_paths = [None, None, None]
        self.sprite_thumbs = [None, None, None]
        self.output_dir = ""
        self.prefix = tk.StringVar()

        self.load_config()
        self.build_gui()
        self.apply_dark_mode()  # apply dark mode by default

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.sprite_paths = config.get('sprites', [None, None, None])
                self.audio_dir = config.get('last_audio_dir', '')
                self.output_dir = config.get('last_output_dir', '')
                self.prefix.set(config.get('prefix', ''))

    def save_config(self):
        config = {
            'sprites': self.sprite_paths,
            'last_audio_dir': self.audio_dir,
            'last_output_dir': self.output_dir,
            'prefix': self.prefix.get()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    def build_gui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)

        # Dark mode toggle checkbox
        mode_frame = ttk.Frame(left_frame)
        mode_frame.pack(fill='x', pady=(0,10))
        self.mode_var = tk.BooleanVar(value=False)  # False means Light Mode off, i.e. Dark on
        self.mode_check = ttk.Checkbutton(mode_frame, text="Light Mode", variable=self.mode_var, command=self.toggle_mode)
        self.mode_check.pack(anchor='w')

        dir_frame = ttk.Frame(left_frame)
        dir_frame.pack(fill='x')
        ttk.Label(dir_frame, text="Audio Folder:").pack(side='left')
        self.dir_entry = ttk.Entry(dir_frame, width=50)
        self.dir_entry.pack(side='left', padx=5)
        self.dir_entry.insert(0, self.audio_dir)
        ttk.Button(dir_frame, text="Browse", command=self.browse_folder).pack(side='left')

        prefix_frame = ttk.Frame(left_frame)
        prefix_frame.pack(fill='x', pady=5)
        ttk.Label(prefix_frame, text="Character name:").pack(side='left')
        ttk.Entry(prefix_frame, textvariable=self.prefix, width=20).pack(side='left', padx=5)

        self.file_listbox = tk.Listbox(left_frame, height=10)
        self.file_listbox.pack(fill='both', expand=True, pady=5)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        sprite_frame = ttk.Frame(left_frame)
        sprite_frame.pack(pady=5)
        self.sprite_labels = []
        self.sprite_thumb_labels = []
        for i in range(3):
            frame = ttk.Frame(sprite_frame)
            frame.pack(side='left', padx=10)
            label = ttk.Label(frame, text=f"Lipstage {i+1}")
            label.pack()
            self.sprite_labels.append(label)
            thumb_label = ttk.Label(frame)
            thumb_label.pack(pady=2)
            self.sprite_thumb_labels.append(thumb_label)
            ttk.Button(frame, text="Choose/Replace", command=lambda idx=i: self.choose_sprite(idx)).pack()

        self.preview_label = ttk.Label(right_frame, anchor='center')
        self.preview_label.pack(fill='both', expand=True)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Play Preview", command=self.play_preview).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Generate .rpy", command=self.prompt_output_and_generate).pack(side='left', padx=10)

        self.output_text = tk.Text(self.root, height=8, bg='#111', fg='#0f0')
        self.output_text.pack(fill='x')
        self.output_text.insert(tk.END, 'Lipsync GUI started.\n')
        self.output_text.config(state='disabled')

        if self.audio_dir:
            self.load_audio_files()
        for i, path in enumerate(self.sprite_paths):
            if path and os.path.exists(path):
                img = Image.open(path)
                self.sprites[i] = img.resize((1000, 1000))
                thumb = img.resize((60, 60))
                thumb_img = ImageTk.PhotoImage(thumb)
                self.sprite_thumbs[i] = thumb_img
                self.sprite_thumb_labels[i].configure(image=thumb_img)
                self.sprite_thumb_labels[i].image = thumb_img

    def toggle_mode(self):
        if self.mode_var.get():
            self.dark_mode = False
            self.apply_light_mode()
        else:
            self.dark_mode = True
            self.apply_dark_mode()

    def apply_dark_mode(self):
        # Set colors for dark mode
        bg_color = '#111111'
        fg_color = '#f0f0f0'
        entry_bg = '#222222'
        entry_fg = '#f0f0f0'
        text_bg = '#111111'
        text_fg = '#0f0'

        style = ttk.Style()
        style.theme_use('clam')

        # Frame backgrounds
        self.root.configure(bg=bg_color)
        for widget in self.root.winfo_children():
            try:
                widget.configure(background=bg_color)
            except:
                pass

        # Update widgets colors
        def recursive_configure(widget):
            for child in widget.winfo_children():
                if isinstance(child, (ttk.Frame, ttk.LabelFrame)):
                    try:
                        child.configure(style='Dark.TFrame')
                    except:
                        pass
                    recursive_configure(child)
                elif isinstance(child, ttk.Label):
                    try:
                        child.configure(foreground=fg_color, background=bg_color)
                    except:
                        pass
                elif isinstance(child, ttk.Button):
                    try:
                        child.configure(style='Dark.TButton')
                    except:
                        pass
                elif isinstance(child, ttk.Entry):
                    child.configure(foreground=entry_fg)
                    # Entry bg on ttk is tricky; fallback to tk.Entry if needed
                    try:
                        child.configure(background=entry_bg)
                    except:
                        pass
                elif isinstance(child, tk.Listbox):
                    child.configure(bg=entry_bg, fg=entry_fg, selectbackground='#444444', selectforeground=fg_color)
                elif isinstance(child, tk.Text):
                    child.configure(bg=text_bg, fg=text_fg)
                recursive_configure(child)

        recursive_configure(self.root)

        style.configure('Dark.TFrame', background=bg_color)
        style.configure('Dark.TButton', background='#333333', foreground=fg_color)
        style.map('Dark.TButton',
                  background=[('active', '#555555')])
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TEntry', fieldbackground=entry_bg, foreground=entry_fg)

        # Update output text colors
        self.output_text.configure(bg=text_bg, fg=text_fg, insertbackground=fg_color)

    def apply_light_mode(self):
        # Set colors for light mode
        bg_color = '#f0f0f0'
        fg_color = "#474747"
        entry_bg = '#ffffff'
        entry_fg = "#3D3D3D"
        text_bg = '#ffffff'
        text_fg = '#008000'

        style = ttk.Style()
        style.theme_use('clam')

        self.root.configure(bg=bg_color)
        for widget in self.root.winfo_children():
            try:
                widget.configure(background=bg_color)
            except:
                pass

        def recursive_configure(widget):
            for child in widget.winfo_children():
                if isinstance(child, (ttk.Frame, ttk.LabelFrame)):
                    try:
                        child.configure(style='Light.TFrame')
                    except:
                        pass
                    recursive_configure(child)
                elif isinstance(child, ttk.Label):
                    try:
                        child.configure(foreground=fg_color, background=bg_color)
                    except:
                        pass
                elif isinstance(child, ttk.Button):
                    try:
                        child.configure(style='Light.TButton')
                    except:
                        pass
                elif isinstance(child, ttk.Entry):
                    child.configure(foreground=entry_fg)
                    try:
                        child.configure(background=entry_bg)
                    except:
                        pass
                elif isinstance(child, tk.Listbox):
                    child.configure(bg=entry_bg, fg=entry_fg, selectbackground='#cccccc', selectforeground=fg_color)
                elif isinstance(child, tk.Text):
                    child.configure(bg=text_bg, fg=text_fg)
                recursive_configure(child)

        recursive_configure(self.root)

        style.configure('Light.TFrame', background=bg_color)
        style.configure('Light.TButton', background='#e0e0e0', foreground=fg_color)
        style.map('Light.TButton',
                  background=[('active', '#c0c0c0')])
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TEntry', fieldbackground=entry_bg, foreground=entry_fg)

        self.output_text.configure(bg=text_bg, fg=text_fg, insertbackground=fg_color)

    def prompt_output_and_generate(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir = folder
            self.save_config()
            self.generate_rpy_all()

    def print_debug(self, text):
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, text + '\n')
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')

    def browse_folder(self):
        directory = filedialog.askdirectory()
        if directory:
            self.audio_dir = directory
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.load_audio_files()
            self.save_config()
            self.print_debug(f"Audio folder set: {directory}")

    def load_audio_files(self):
        self.audio_files = [f for f in os.listdir(self.audio_dir) if f.lower().endswith(('.wav', '.ogg', '.flac', '.mp3'))]
        self.file_listbox.delete(0, tk.END)
        for f in self.audio_files:
            self.file_listbox.insert(tk.END, f)
        self.print_debug(f"Loaded {len(self.audio_files)} audio files.")

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            self.selected_audio = self.audio_files[selection[0]]
            self.print_debug(f"Selected: {self.selected_audio}")

    def choose_sprite(self, index):
        filepath = filedialog.askopenfilename(filetypes=[("PNG Images", "*.png")])
        if filepath:
            img = Image.open(filepath)
            self.sprites[index] = img.resize((1000, 1000))
            self.sprite_paths[index] = filepath
            thumb = img.resize((60, 60))
            thumb_img = ImageTk.PhotoImage(thumb)
            self.sprite_thumbs[index] = thumb_img
            self.sprite_thumb_labels[index].configure(image=thumb_img)
            self.sprite_thumb_labels[index].image = thumb_img
            self.save_config()
            self.print_debug(f"Set Lipstage {index+1}: {filepath}")

    def play_preview(self):
        if not self.selected_audio:
            messagebox.showerror("Error", "Please select an audio file.")
            return
        if not all(self.sprites):
            messagebox.showerror("Error", "Please set all 3 lipstage sprites.")
            return

        audio_path = os.path.join(self.audio_dir, self.selected_audio)
        threading.Thread(target=self._play_lipsync_preview, args=(audio_path,), daemon=True).start()

    def _play_lipsync_preview(self, filepath):
        data, samplerate = sf.read(filepath)
        chunk_size = int(samplerate * 0.05)
        max_sample = np.iinfo(np.int16).max if data.dtype == np.int16 else 1.0
        max_db = 20 * np.log10(np.max(np.abs(data)) / max_sample + 1e-12) + 240
        lower_limit = max_db - 30
        upper_limit = max_db - 12

        def get_lip_stage(chunk, last_stage):
            peak = np.max(np.abs(chunk)) / max_sample
            db = 20 * math.log10(max(peak, 1e-12)) + 240
            if db < lower_limit:
                self.print_debug(f"0")
                return 0
            elif db < upper_limit:
                self.print_debug(f"1")
                return 1
            else:
                self.print_debug(f"2")
                return 2

        def display_stage(index):
            img = ImageTk.PhotoImage(self.sprites[index].resize((1000, 1000)))
            self.preview_label.configure(image=img)
            self.preview_label.image = img

        sd.play(data, samplerate)
        last_stage = 0
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            if chunk.ndim > 1:
                chunk = np.mean(chunk, axis=1)
            stage = get_lip_stage(chunk, last_stage)
            last_stage = stage
            self.root.after(0, display_stage, stage)
            time.sleep(0.05)
        if last_stage != 0:
            self.root.after(0, display_stage, 0)
        sd.stop()
        self.print_debug(f"Finished playing: {os.path.basename(filepath)}")

    def generate_rpy(self):
        name = os.path.splitext(self.selected_audio)[0]
        filepath = os.path.join(self.audio_dir, self.selected_audio)
        data, samplerate = sf.read(filepath)
        chunk_size = int(samplerate * 0.05)
        max_sample = np.iinfo(np.int16).max if data.dtype == np.int16 else 1.0
        max_db = 20 * np.log10(np.max(np.abs(data)) / max_sample + 1e-12) + 240
        lower_limit = max_db - 30
        upper_limit = max_db - 12
        stages = []
        last_stage = 1
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            if chunk.ndim > 1:
                chunk = np.mean(chunk, axis=1)
            peak = np.max(np.abs(chunk)) / max_sample
            db = 20 * math.log10(max(peak, 1e-12)) + 240
            if db < lower_limit:
                stage = 1
            elif db < upper_limit:
                stage = 2
            else:
                stage = 3
            last_stage = stage
            stages.append(stage)

        if last_stage != 1:
            stages.append(1)

        rpy_output = os.path.join(self.output_dir or self.audio_dir, name + '.rpy')
        prefix = self.prefix.get().strip() or name.split('_')[0]
        with open(rpy_output, 'w') as f:
            f.write(f'image {name}:\n')
            last = None
            acc = 0.0
            for stage in stages:
                current = f'    "/sprites/{prefix}/[{prefix}_pose]/[{prefix}_face]/[{prefix}_lipstage{stage}].png"'
                if current == last:
                    acc += 0.05
                else:
                    if last:
                        f.write(f'{last}\n    {acc:.2f}\n')
                    last = current
                    acc = 0.05
            if last:
                f.write(f'{last}\n    {acc:.2f}\n')

        self.print_debug(f'Generated: {rpy_output}')


if __name__ == '__main__':
    root = tk.Tk()

    try:
        root.iconbitmap('icon.ico')
    except Exception:
        pass

    try:
        icon_img = ImageTk.PhotoImage(file='icon.png')
        root.wm_iconphoto(True, icon_img)
    except Exception:
        pass

    app = LipsyncGUI(root)
    root.mainloop()





