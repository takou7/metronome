import tkinter as tk
from tkinter import ttk
import pygame
import numpy as np
import os

class MetronomeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("metronome")
        self.root.geometry("400x600")
        
        self.root.resizable(False, False)
        
        
        self.root.bind('<Right>', lambda event: self.change_bpm(10))
        self.root.bind('<Left>',  lambda event: self.change_bpm(-10))
        self.root.bind('<Up>',    lambda event: self.change_bpm(1))
        self.root.bind('<Down>',  lambda event: self.change_bpm(-1))
        self.root.bind('<space>', self.on_space_pressed)
        
        
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except pygame.error as e:
            print(f"オーディオ初期化エラー: {e}")

        
        self.is_running = False
        self.timer_id = None
        
        self.bpm = tk.IntVar(value=120)
        self.beat_count = tk.IntVar(value=4) # 0 = なし
        self.current_beat_index = 0
        self.volume = tk.IntVar(value=50)
        self.is_visual_on = tk.BooleanVar(value=True)
        self.is_always_on_top = tk.BooleanVar(value=True)
        self.sound_mode = tk.StringVar(value="Beep")
        
        self.update_always_on_top()

       
        self.create_widgets()
        
        
        self.sounds = {}
        self.generate_beep_sounds()
        self.load_drum_sounds()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

       
        self.canvas = tk.Canvas(main_frame, width=240, height=60, bg="#222222", highlightthickness=0)
        self.canvas.pack(pady=(0, 20))
        self.indicators = []
        for i in range(4):
            x = 25 + i * 55
            oval = self.canvas.create_oval(x, 15, x+30, 45, fill="#444444", outline="")
            self.indicators.append(oval)

        
        bpm_frame = ttk.LabelFrame(main_frame, text="テンポ (BPM)", padding=10)
        bpm_frame.pack(fill="x", pady=5)
        
        self.bpm_label = ttk.Label(bpm_frame, text=f"{self.bpm.get()}", font=("Arial", 20, "bold"), anchor="center")
        self.bpm_label.pack()

        self.bpm_scale = ttk.Scale(bpm_frame, from_=30, to=400, variable=self.bpm, command=self.update_bpm_from_slider)
        self.bpm_scale.pack(fill="x", pady=5)

        btn_frame = ttk.Frame(bpm_frame)
        btn_frame.pack(fill="x", pady=5)
        btn_frame.columnconfigure((0,1,2,3), weight=1)

        ttk.Button(btn_frame, text="-10", command=lambda: self.change_bpm(-10)).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text="-1", command=lambda: self.change_bpm(-1)).grid(row=0, column=1, padx=2)
        ttk.Button(btn_frame, text="+1", command=lambda: self.change_bpm(1)).grid(row=0, column=2, padx=2)
        ttk.Button(btn_frame, text="+10", command=lambda: self.change_bpm(10)).grid(row=0, column=3, padx=2)
        
        ttk.Label(bpm_frame, text="※キーボード操作: [Space 再生/停止] [↑↓/←→ BPM変更]", font=("Meiryo UI", 8), foreground="gray").pack(pady=(5,0))

        
        beat_frame = ttk.LabelFrame(main_frame, text="拍子設定", padding=10)
        beat_frame.pack(fill="x", pady=5)
        
       
        beats = [("なし", 0), ("1拍子", 1), ("2拍子", 2), ("3拍子", 3), ("4拍子", 4), ("6拍子", 6)]
        
        self.beat_combo = ttk.Combobox(beat_frame, values=[b[0] for b in beats], state="readonly")
        self.beat_combo.current(4) 
        self.beat_combo.pack(fill="x")
        self.beat_combo.bind("<<ComboboxSelected>>", self.update_beat_count)

        
        sound_frame = ttk.LabelFrame(main_frame, text="サウンド設定", padding=10)
        sound_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(sound_frame, text="電子音", variable=self.sound_mode, value="Beep").pack(anchor="w")
        self.drum_rb = ttk.Radiobutton(sound_frame, text="ドラム (要wavファイル)", variable=self.sound_mode, value="Drum")
        self.drum_rb.pack(anchor="w")

        vol_box = ttk.Frame(sound_frame)
        vol_box.pack(fill="x", pady=(10, 0))
        
        self.vol_label = ttk.Label(vol_box, text=f"音量: {self.volume.get()}%", width=10)
        self.vol_label.pack(side="left")
        
        self.vol_scale = tk.Scale(vol_box, from_=0, to=100, resolution=1, orient="horizontal", variable=self.volume, command=self.update_volume, showvalue=False, bg="#f0f0f0", bd=0, highlightthickness=0)
        self.vol_scale.pack(side="left", fill="x", expand=True)

        
        opt_frame = ttk.Frame(main_frame)
        opt_frame.pack(fill="x", pady=10)
        ttk.Checkbutton(opt_frame, text="視覚効果", variable=self.is_visual_on).pack(side="left")
        ttk.Checkbutton(opt_frame, text="常に手前に表示", variable=self.is_always_on_top, command=self.update_always_on_top).pack(side="left", padx=10)

        
        self.toggle_btn = tk.Button(main_frame, text="START", font=("Arial", 16, "bold"), bg="#dddddd", command=self.toggle_start)
        self.toggle_btn.pack(fill="x", pady=10, ipady=15)


    def update_always_on_top(self):
        self.root.attributes('-topmost', self.is_always_on_top.get())

    def update_beat_count(self, event):
        val = self.beat_combo.get()
        
        if val == "なし":
            self.beat_count.set(0)
        else:
            self.beat_count.set(int(val.replace("拍子", "")))

    def update_volume(self, val):
        vol_int = int(float(val))
        self.vol_label.config(text=f"音量: {vol_int}%")
        vol_float = vol_int / 100.0
        for key in self.sounds:
            if self.sounds[key]: self.sounds[key].set_volume(vol_float)

    def update_bpm_from_slider(self, val):
        self.bpm_label.config(text=f"{int(float(val))}")

    def change_bpm(self, delta):
        current = self.bpm.get()
        new_bpm = current + delta
        if new_bpm < 30: new_bpm = 30
        if new_bpm > 400: new_bpm = 400
        self.bpm.set(new_bpm)
        self.bpm_label.config(text=f"{new_bpm}")

    def generate_beep_sounds(self):
        def make_sound(freq, duration=0.1):
            sample_rate = 44100
            n_samples = int(sample_rate * duration)
            t = np.linspace(0, duration, n_samples, False)
            wave = 0.5 * np.sign(np.sin(2 * np.pi * freq * t))
            sound_data = np.column_stack((wave, wave)).astype(np.float32)
            return pygame.sndarray.make_sound((sound_data * 32767).astype(np.int16))

        self.beep_high = make_sound(880)
        self.beep_low = make_sound(440)
        self.sounds["Beep_High"] = self.beep_high
        self.sounds["Beep_Low"] = self.beep_low
        init_vol = self.volume.get() / 100.0
        self.beep_high.set_volume(init_vol)
        self.beep_low.set_volume(init_vol)

    def load_drum_sounds(self):
        files = {"Drum_High": "kick.wav", "Drum_Low": "snare.wav"}
        self.has_drums = True
        for key, filename in files.items():
            if os.path.exists(filename):
                try:
                    self.sounds[key] = pygame.mixer.Sound(filename)
                except:
                    self.has_drums = False
            else:
                self.has_drums = False
        
        if self.has_drums:
            init_vol = self.volume.get() / 100.0
            for key in ["Drum_High", "Drum_Low"]:
                if key in self.sounds: self.sounds[key].set_volume(init_vol)
        else:
            self.drum_rb.config(state="disabled", text="ドラム (ファイル無し)")

    def on_space_pressed(self, event):
        if self.root.focus_get() == self.toggle_btn:
            return
        self.toggle_start()

    def toggle_start(self):
        if self.is_running:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.current_beat_index = 0
        self.toggle_btn.config(text="STOP", bg="#ffcccc")
        self.tick()

    def stop(self):
        self.is_running = False
        self.toggle_btn.config(text="START", bg="#dddddd")
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        for oval in self.indicators:
            self.canvas.itemconfig(oval, fill="#444444")

    def tick(self):
        if not self.is_running:
            return

        beat_max = self.beat_count.get()
        
        
        if beat_max == 0:
            is_first_beat = False
        else:
            is_first_beat = (self.current_beat_index == 0)

        
        mode = self.sound_mode.get()
        sound_to_play = None
        if mode == "Drum" and self.has_drums:
            sound_to_play = self.sounds["Drum_High"] if is_first_beat else self.sounds["Drum_Low"]
        else:
            sound_to_play = self.sounds["Beep_High"] if is_first_beat else self.sounds["Beep_Low"]
        
        if sound_to_play:
            sound_to_play.play()

        
        if self.is_visual_on.get():
            self.flash_indicator(self.current_beat_index % 4, is_first_beat)

        
        bpm = self.bpm.get()
        if bpm <= 0: bpm = 60
        interval_ms = int(60000 / bpm)

        
        if beat_max == 0:
            self.current_beat_index = (self.current_beat_index + 1) % 4
        else:
            self.current_beat_index = (self.current_beat_index + 1) % beat_max
        
        self.timer_id = self.root.after(interval_ms, self.tick)

    def flash_indicator(self, index, is_accent):
        for oval in self.indicators:
            self.canvas.itemconfig(oval, fill="#444444")
        
        color = "#FD7597" if is_accent else "#97FF6E"
        disp_index = index % len(self.indicators)
        self.canvas.itemconfig(self.indicators[disp_index], fill=color)

        self.root.after(100, lambda: self.canvas.itemconfig(self.indicators[disp_index], fill="#444444") if self.is_running else None)

    def on_closing(self):
        self.stop()
        try:
            pygame.mixer.quit()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MetronomeApp(root)
    root.mainloop()