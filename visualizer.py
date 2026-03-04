import tkinter as tk
from tkinter import ttk
import os
import re
from datetime import datetime

# ====================== КОНФИГУРАЦИЯ СЕТИ (точно как в node9.py) ======================
positions = {
    'A': (0, 100), 'B': (50, 120), 'C': (50, 80),
    'D': (50, 40), 'E': (100, 100)
}

table_round = {
    'A': ['B', 'C', 'D'],
    'B': ['A', 'C', 'E'],
    'C': ['A', 'B', 'D', 'E'],
    'D': ['A', 'C', 'E'],
    'E': ['B', 'C', 'D'],
}

# Начальные пакеты (точно как в вашей программе)
initial_packets = {
    'A': set(range(1, 11)),
    'B': set(range(5, 11)),
    'C': set(range(4, 8)),
    'D': set(range(1, 6)),
    'E': set()
}

COLOR_MAP = {
    'BEACON': '#808080',
    'KNOWN-FULLSET': '#800080',
    'RETRANSLATION': '#FF8C00',
    'REQUEST-PACKETS': '#1E90FF',
    'PACKETS': '#32CD32',
}

HIGHLIGHT_SENDER = '#FF4500'
HIGHLIGHT_RECEIVER = '#32CD32'   # для приёма
DEFAULT_NODE = '#ADD8E6'

class NetworkVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Визуализатор сети — logs.txt (полная привязка к логам)")
        self.root.geometry("1380x820")

        self.events = []
        self.current_index = 0
        self.playing = False
        self.speed = 1.0

        # Пакеты у каждого узла (обновляются только по реальным "Получил PACKETS")
        self.node_packets = {nid: s.copy() for nid, s in initial_packets.items()}

        self.create_widgets()
        self.load_logs()

    def create_widgets(self):
        # ==================== CANVAS ====================
        self.canvas = tk.Canvas(self.root, bg="#F0F0F0", width=800, height=540)
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        # ==================== ПРАВАЯ ПАНЕЛЬ (пакеты) ====================
        right = ttk.Frame(self.root, width=320)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        ttk.Label(right, text="Пакеты у узлов (обновляются по логам)", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,8))

        self.packet_labels = {}
        for nid in 'ABCDE':
            f = ttk.LabelFrame(right, text=f"Узел {nid}")
            f.pack(fill=tk.X, pady=3)
            lbl = ttk.Label(f, text="[]", font=("Consolas", 10), anchor="w")
            lbl.pack(padx=10, pady=6, fill=tk.X)
            self.packet_labels[nid] = lbl

        self.sink_phrase = ttk.Label(right, text="Фраза у E: —", font=("Arial", 11, "bold"),
                                     foreground="#006400", wraplength=280)
        self.sink_phrase.pack(pady=20, fill=tk.X)

        self.update_packet_display()

        # ==================== УПРАВЛЕНИЕ ====================
        ctrl = ttk.Frame(self.root)
        ctrl.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Button(ctrl, text="📂 Загрузить логи", command=self.load_logs).pack(side=tk.LEFT, padx=5)
        self.btn_play = ttk.Button(ctrl, text="▶ Воспроизвести", command=self.toggle_play)
        self.btn_play.pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="⏹ Стоп", command=self.stop_play).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="⏭ Шаг", command=self.step_forward).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="🔄 Сброс", command=self.reset).pack(side=tk.LEFT, padx=5)

        ttk.Label(ctrl, text="Скорость:").pack(side=tk.LEFT, padx=(30,5))
        self.speed_var = tk.StringVar(value="1x")
        cb = ttk.Combobox(ctrl, textvariable=self.speed_var, values=["0.5x","1x","2x","5x","10x"], width=6, state="readonly")
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: setattr(self, 'speed', float(self.speed_var.get().replace("x",""))))

        # ==================== ТЕКУЩЕЕ СОБЫТИЕ ====================
        self.info_label = ttk.Label(self.root, text="—", font=("Consolas", 11), anchor="w", wraplength=750)
        self.info_label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # ==================== ЛОГ ====================
        logf = ttk.LabelFrame(self.root, text="Журнал событий")
        logf.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.logbox = tk.Listbox(logf, font=("Consolas", 9), height=13)
        scroll = ttk.Scrollbar(logf, orient=tk.VERTICAL, command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=scroll.set)
        self.logbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.draw_network()

    def draw_network(self):
        self.canvas.delete("all")
        SCALE = 4.8
        OX, OY = 90, 50
        R = 23

        for nid, (x, y) in positions.items():
            cx = OX + x * SCALE
            cy = OY + (120 - y) * SCALE

            oval = self.canvas.create_oval(cx-R, cy-R, cx+R, cy+R,
                                           fill=DEFAULT_NODE, outline="#333", width=3, tags=nid)
            setattr(self, f"oval_{nid}", oval)

            self.canvas.create_text(cx, cy+R+22, text=nid, font=("Arial", 14, "bold"))
            self.canvas.create_text(cx, cy+R+40, text=f"({int(x)},{int(y)})", font=("Arial", 8), fill="#555")

        self.canvas.create_text(400, 20, text="Ненаправленная передача (стрелки по логам)", font=("Arial", 12, "bold"))

    def load_logs(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs.txt")
        if not os.path.exists(path):
            self.info_label.config(text=f"❌ logs.txt не найден!\n{path}")
            return

        self.events.clear()
        self.logbox.delete(0, tk.END)

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 4: continue
                ts, node, op, target = parts[:4]
                details = parts[4] if len(parts) > 4 else ""
                self.events.append((line, ts, node, op, target, details))
                self.logbox.insert(tk.END, line)

        if self.events:
            self.info_label.config(text=f"✅ Загружено {len(self.events)} событий из логов")
            self.reset()

    def update_packet_display(self):
        for nid in 'ABCDE':
            lst = sorted(self.node_packets[nid])
            txt = f"[{', '.join(map(str, lst))}]" if lst else "[]"
            self.packet_labels[nid].config(text=txt)

        # Фраза у стока E
        if len(self.node_packets['E']) == 10:
            words = ['Каждый',' ','Охотник',' ','желает',' ','знать',',',' ','где']
            phrase = ''.join(words[i-1] for i in sorted(self.node_packets['E']))
            self.sink_phrase.config(text=f"Фраза у E: «{phrase}» ✅")
        else:
            self.sink_phrase.config(text=f"Фраза у E: {len(self.node_packets['E'])}/10 пакетов")

    def get_canvas_pos(self, nid):
        SCALE = 4.8
        OX, OY = 90, 50
        x, y = positions[nid]
        return OX + x * SCALE, OY + (120 - y) * SCALE

    def process_event(self, event_tuple):
        full_line, ts, node, op, target, details = event_tuple
        self.info_label.config(text=f"{ts} | {node} | {op} | {target} | {details[:65]}...")

        self.logbox.see(tk.END)

        msg_type = op.split()[-1].upper() if " " in op else op.upper()
        msg_color = COLOR_MAP.get(msg_type, "#000000")

        # ==================== ОТПРАВКА (рисуем стрелки ко всем в радиусе) ====================
        if "Отправка" in op:
            # Всегда отправляем всем соседям (ненаправленная передача)
            neighbors = table_round.get(node, [])

            # Подсвечиваем отправителя
            self.highlight_node(node, HIGHLIGHT_SENDER)

            sx, sy = self.get_canvas_pos(node)
            for tgt in neighbors:
                if tgt == node: continue
                tx, ty = self.get_canvas_pos(tgt)

                # Если указан конкретный получатель (не ALL) и это он — яркая стрелка
                if target != "ALL" and tgt == target:
                    arrow_color = "#00FF7F"      # ярко-зелёный для целевого получателя
                    width = 4.5
                    dash = None
                else:
                    arrow_color = "#A0A0A0"      # серый — слышат, но не предназначено
                    width = 2.2
                    dash = (4, 2)

                line = self.canvas.create_line(sx, sy, tx, ty,
                                               fill=arrow_color, width=width,
                                               arrow=tk.LAST, dash=dash, tags="temp_arrow")
                self.root.after(1700, lambda lid=line: self.canvas.delete(lid))

        # ==================== ПРИЁМ (заливка узла + добавление пакетов) ====================
        elif "Получил" in op:
            # Подсвечиваем получателя цветом сообщения
            self.highlight_node(node, msg_color)

            # Если это PACKETS — добавляем пакеты получателю (только по логам!)
            if msg_type == "PACKETS" and details:
                match = re.search(r'\[([\d,\s]+)\]', details)
                if match:
                    nums = [int(x.strip()) for x in match.group(1).split(',') if x.strip()]
                    self.node_packets[node].update(nums)
                    self.update_packet_display()

            # Стрелка от отправителя к получателю (короткая)
            if target in positions and target != node:
                sx, sy = self.get_canvas_pos(target)
                tx, ty = self.get_canvas_pos(node)
                line = self.canvas.create_line(sx, sy, tx, ty,
                                               fill=msg_color, width=2.8, arrow=tk.LAST, tags="temp_arrow")
                self.root.after(850, lambda lid=line: self.canvas.delete(lid))

    def highlight_node(self, nid, color):
        oval = getattr(self, f"oval_{nid}", None)
        if oval:
            old = self.canvas.itemcget(oval, "fill")
            self.canvas.itemconfig(oval, fill=color)
            self.root.after(650, lambda: self.canvas.itemconfig(oval, fill=DEFAULT_NODE))

    # ====================== ВОСПРОИЗВЕДЕНИЕ ======================
    def toggle_play(self):
        self.playing = not self.playing
        self.btn_play.config(text="⏸ Пауза" if self.playing else "▶ Воспроизвести")
        if self.playing and self.current_index < len(self.events):
            self.play_step()

    def stop_play(self):
        self.playing = False
        self.btn_play.config(text="▶ Воспроизвести")

    def step_forward(self):
        if self.current_index < len(self.events):
            self.process_event(self.events[self.current_index])
            self.current_index += 1

    def reset(self):
        self.stop_play()
        self.current_index = 0
        self.canvas.delete("temp_arrow")
        self.node_packets = {nid: s.copy() for nid, s in initial_packets.items()}
        self.update_packet_display()
        self.info_label.config(text="— сброшено —")

    def play_step(self):
        if not self.playing or self.current_index >= len(self.events):
            self.stop_play()
            return

        self.process_event(self.events[self.current_index])
        self.current_index += 1

        # Реальная задержка из лога
        if self.current_index < len(self.events):
            t1 = self.ts_to_sec(self.events[self.current_index-1][1])
            t2 = self.ts_to_sec(self.events[self.current_index][1])
            delay = max(int((t2 - t1) * 1000 / self.speed), 40)
        else:
            delay = 700

        self.root.after(delay, self.play_step)

    def ts_to_sec(self, ts):
        try:
            h, m, s = ts.split(':')
            return int(h)*3600 + int(m)*60 + float(s)
        except:
            return 0


if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkVisualizer(root)
    root.mainloop()