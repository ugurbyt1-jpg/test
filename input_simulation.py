"""
Hardware Input Abstraction Layer
================================
Low-level input simulation with biometric patterns
"""

import ctypes
import os
import time
import random
import math
from ctypes import wintypes

# ========== CONFIGURATION ==========
# Anti-cheat: Dosya yollarını obfuscate et
_DRV_PATHS = [
    os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'LGHUB', 'ghub_device.dll'),
    os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'Logitech Gaming Software', 'SDK', 'ghub_device.dll'),
    os.path.join(os.getcwd(), 'ghub_device.dll')
]
LOGITECH_PATHS = _DRV_PATHS

# ========== SCANCODES ==========
SCANCODES = {
    'esc': 0x01, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B, '-': 0x0C,
    '=': 0x0D, 'backspace': 0x0E, 'tab': 0x0F, 'q': 0x10, 'w': 0x11,
    'e': 0x12, 'r': 0x13, 't': 0x14, 'y': 0x15, 'u': 0x16, 'i': 0x17,
    'o': 0x18, 'p': 0x19, '[': 0x1A, ']': 0x1B, 'enter': 0x1C, 'ctrl': 0x1D,
    'a': 0x1E, 's': 0x1F, 'd': 0x20, 'f': 0x21, 'g': 0x22, 'h': 0x23,
    'j': 0x24, 'k': 0x25, 'l': 0x26, ';': 0x27, "'": 0x28, '`': 0x29,
    'lshift': 0x2A, '\\': 0x2B, 'z': 0x2C, 'x': 0x2D, 'c': 0x2E, 'v': 0x2F,
    'b': 0x30, 'n': 0x31, 'm': 0x32, ',': 0x33, '.': 0x34, '/': 0x35,
    'rshift': 0x36, 'prtscr': 0x37, 'alt': 0x38, 'space': 0x39, 'capslock': 0x3A,
    'f1': 0x3B, 'f2': 0x3C, 'f3': 0x3D, 'f4': 0x3E, 'f5': 0x3F, 'f6': 0x40,
    'f7': 0x41, 'f8': 0x42, 'f9': 0x43, 'f10': 0x44, 'numlock': 0x45,
    'scrolllock': 0x46, 'home': 0x47, 'up': 0x48, 'pageup': 0x49, '-': 0x4A,
    'left': 0x4B, 'center': 0x4C, 'right': 0x4D, '+': 0x4E, 'end': 0x4F,
    'down': 0x50, 'pagedown': 0x51, 'insert': 0x52, 'delete': 0x53
}

# ========== CTYPES STRUCTURES (GLOBAL) ==========
# 64-bit uyumlu yapı tanımları
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ULONG_PTR)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ULONG_PTR)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("union", INPUT_UNION)]

# Input Types
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Key Flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Mouse Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000

class InputSimulator:
    def __init__(self):
        self.mode = "WIN32_HUMANIZED"
        self.ghub = None
        self._load_driver()
        
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        
        # Biyolojik Simülasyon Değişkenleri
        self.start_time = time.time()
        self.action_count = 0

    def get_fatigue_multiplier(self):
        """Zamanla artan yorgunluk katsayısı"""
        # Çalışma süresi (saat cinsinden)
        elapsed_hours = (time.time() - self.start_time) / 3600.0
        
        # Her saat %3 yavaşlama ekle, maksimum %25 yavaşla
        fatigue_factor = min(0.25, elapsed_hours * 0.03)
        
        # Anlık enerji dalgalanması (Adrenalin simülasyonu: +/- %5)
        energy_fluctuation = random.uniform(-0.05, 0.05)
        
        return 1.0 + fatigue_factor + energy_fluctuation

    def _check_focus_loss(self):
        """Dikkatsizlik ve odak kaybı simülasyonu (Micro-Pauses)"""
        # Her işlemde çok düşük ihtimalle kısa bir duraksama
        if random.random() < 0.01: # %1 ihtimal
            # 0.3 ile 1.2 saniye arası "Ekrana bakma / Düşünme" süresi
            pause = random.uniform(0.3, 1.2)
            time.sleep(pause)

    def _load_driver(self):
        local_dll = os.path.join(os.getcwd(), "ghub_device.dll")
        if os.path.exists(local_dll):
            try:
                self.ghub = ctypes.CDLL(local_dll)
                try: self.ghub.device_open()
                except: pass
                self.mode = "LOGITECH_DRIVER"
                print(f"[GHOST] ✅ Logitech Sürücüsü (Yerel) Yüklendi: {local_dll}")
                return
            except: pass

        for path in LOGITECH_PATHS:
            if os.path.exists(path):
                try:
                    self.ghub = ctypes.CDLL(path)
                    try: self.ghub.device_open()
                    except: pass
                    self.mode = "LOGITECH_DRIVER"
                    print(f"[GHOST] ✅ Logitech Sürücüsü Bulundu: {path}")
                    return
                except: pass
        
        print("[GHOST] ⚠️ Logitech Sürücüsü (ghub_device.dll) bulunamadı.")
        print("[GHOST] ℹ️ Yeni nesil G-Hub sürümlerinde bu dosya gizlidir.")
        print("[GHOST] 🚀 Gelişmiş 'Humanized Win32' modu devreye alındı (Güvenli).")

    def _get_scancode(self, key):
        return SCANCODES.get(key.lower(), 0)

    def press(self, key, hold_time=None):
        self.action_count += 1
        self._check_focus_loss()
        multiplier = self._get_fatigue_multiplier()
        
        if hold_time is None:
            # Tuş tipine göre biyomekanik süreler
            if key in ['space', 'enter', 'backspace']:
                # Başparmak veya serçe parmak (Daha yavaş)
                base = random.uniform(0.08, 0.15)
            elif key in ['shift', 'ctrl', 'alt']:
                # Modifier tuşlar (Uzun basılır)
                base = random.uniform(0.12, 0.25)
            else:
                # Standart harfler (Hızlı)
                base = random.uniform(0.05, 0.11)
            
            hold_time = base * multiplier

        self.key_down(key)
        time.sleep(hold_time)
        self.key_up(key)
        
        # Tuş sonrası mikro bekleme (Sinaptik gecikme)
        time.sleep(random.uniform(0.01, 0.03) * multiplier)

    def key_down(self, key):
        code = self._get_scancode(key)
        if code == 0: return

        if self.mode == "LOGITECH_DRIVER":
            self.ghub.key_down(code)
        else:
            self._win32_key(code, down=True)

    def key_up(self, key):
        code = self._get_scancode(key)
        if code == 0: return

        if self.mode == "LOGITECH_DRIVER":
            self.ghub.key_up(code)
        else:
            self._win32_key(code, down=False)

    def click(self, button='left'):
        multiplier = self._get_fatigue_multiplier()
        hold = random.uniform(0.05, 0.15) * multiplier
        
        if self.mode == "LOGITECH_DRIVER":
            btn_code = 1 if button == 'left' else 2
            self.ghub.mouse_down(btn_code)
            time.sleep(hold)
            self.ghub.mouse_up(btn_code)
        else:
            self._win32_click(button, True)
            time.sleep(hold)
            self._win32_click(button, False)

    def double_click(self, button='left'):
        multiplier = self._get_fatigue_multiplier()
        self.click(button)
        # İki tıklama arası süre (Yoruldukça artar)
        time.sleep(random.uniform(0.08, 0.15) * multiplier)
        self.click(button)

    def move_to(self, x, y, duration=None):
        """Mouse'u belirtilen noktaya Biyometrik İnsan Simülasyonu ile götürür"""
        self.action_count += 1
        self._check_focus_loss()
        multiplier = self._get_fatigue_multiplier()

        start_pos = self.get_mouse_pos()
        end_pos = (int(x), int(y))
        dist = math.hypot(end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
        
        if duration is None:
            # Fitts's Law benzeri süre hesaplama (Mesafe arttıkça süre artar ama logaritmik)
            duration = (random.uniform(0.15, 0.25) + (dist / 1500.0)) * multiplier

        # %20 İhtimalle "Overshoot" (Hedefi şaşırıp düzeltme) yap
        if dist > 50 and random.random() < 0.20:
            # Hedefi biraz geç veya gerisinde kal
            overshoot_x = end_pos[0] + random.randint(-15, 15)
            overshoot_y = end_pos[1] + random.randint(-15, 15)
            
            # Ana hareket (Hızlı)
            self._move_curve(start_pos, (overshoot_x, overshoot_y), duration * 0.8)
            
            # Düzeltme hareketi (Yavaş ve kısa)
            time.sleep(random.uniform(0.02, 0.05))
            self._move_curve((overshoot_x, overshoot_y), end_pos, duration * 0.3)
        else:
            # Normal hareket
            self._move_curve(start_pos, end_pos, duration)

    def _move_curve(self, start_pos, end_pos, duration):
        """Bezier Eğrisi + Ease-In-Out Hızlanma"""
        control1 = (
            start_pos[0] + (end_pos[0] - start_pos[0]) * 0.3 + random.randint(-50, 50),
            start_pos[1] + (end_pos[1] - start_pos[1]) * 0.3 + random.randint(-50, 50)
        )
        control2 = (
            start_pos[0] + (end_pos[0] - start_pos[0]) * 0.7 + random.randint(-50, 50),
            start_pos[1] + (end_pos[1] - start_pos[1]) * 0.7 + random.randint(-50, 50)
        )

        steps = int(duration * 120) # 120 Hz (Daha akıcı)
        if steps < 5: steps = 5
        
        for i in range(steps):
            t = i / steps
            # Ease-In-Out Fonksiyonu (Yavaş başla, hızlan, yavaş dur)
            # Smoothstep: t * t * (3 - 2 * t)
            ease_t = t * t * (3 - 2 * t)
            
            bx = (1-ease_t)**3 * start_pos[0] + 3*(1-ease_t)**2 * ease_t * control1[0] + 3*(1-ease_t)*ease_t**2 * control2[0] + ease_t**3 * end_pos[0]
            by = (1-ease_t)**3 * start_pos[1] + 3*(1-ease_t)**2 * ease_t * control1[1] + 3*(1-ease_t)*ease_t**2 * control2[1] + ease_t**3 * end_pos[1]
            
            # Fizyolojik Tremor (El titremesi) - 8-12 Hz
            # Yoruldukça titreme artar
            tremor_amp = 1 if self._get_fatigue_multiplier() < 1.1 else 2
            if i % 2 == 0: 
                bx += random.randint(-tremor_amp, tremor_amp)
                by += random.randint(-tremor_amp, tremor_amp)

            self._raw_move(int(bx), int(by))
            
            # Dinamik bekleme (Hız profili için döngü içinde minik sapmalar)
            time.sleep(duration / steps)
            
        self._raw_move(end_pos[0], end_pos[1])

    def _raw_move(self, x, y):
        self._win32_move(x, y)

    def get_mouse_pos(self):
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    # ================= WIN32 LOW LEVEL =================
    def _win32_key(self, scancode, down=True):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki.wVk = 0
        inp.union.ki.wScan = scancode
        inp.union.ki.dwFlags = KEYEVENTF_SCANCODE | (0 if down else KEYEVENTF_KEYUP)
        inp.union.ki.time = 0
        # Anti-cheat: dwExtraInfo'yu rastgele veya gerçekçi değerlerle doldur
        # Windows varsayılan olarak GetMessageExtraInfo() değerini kullanır
        inp.union.ki.dwExtraInfo = ctypes.windll.user32.GetMessageExtraInfo() or random.randint(0, 0xFFFF)
        
        result = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        if result == 0:
            error = ctypes.get_last_error()
            print(f"[WIN32] ❌ SendInput key failed (scancode={scancode}, down={down}): Error {error}")

    def _win32_move(self, x, y):
        nx = int(x * 65535 / self.screen_width)
        ny = int(y * 65535 / self.screen_height)

        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = nx
        inp.union.mi.dy = ny
        inp.union.mi.mouseData = 0
        inp.union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
        inp.union.mi.time = 0
        # Anti-cheat: dwExtraInfo'yu gerçekçi değerlerle doldur
        inp.union.mi.dwExtraInfo = ctypes.windll.user32.GetMessageExtraInfo() or random.randint(0, 0xFFFF)
        
        result = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        if result == 0:
            error = ctypes.get_last_error()
            print(f"[WIN32] ❌ SendInput move failed: Error {error}")

    def _win32_click(self, button, down=True):
        if button == 'left':
            flag = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
        else:
            flag = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP

        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = 0
        inp.union.mi.dy = 0
        inp.union.mi.mouseData = 0
        inp.union.mi.dwFlags = flag
        inp.union.mi.time = 0
        # Anti-cheat: dwExtraInfo'yu gerçekçi değerlerle doldur
        inp.union.mi.dwExtraInfo = ctypes.windll.user32.GetMessageExtraInfo() or random.randint(0, 0xFFFF)
        
        result = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        if result == 0:
            error = ctypes.get_last_error()
            print(f"[WIN32] ❌ SendInput click failed (button={button}, down={down}): Error {error}")

if __name__ == "__main__":
    sim = InputSimulator()
    print("3 saniye sonra test başlıyor...")
    time.sleep(3)
    print("Mouse hareketi...")
    sim.move_to(500, 500)
    print("Yazı yazılıyor...")
    for char in "merhaba":
        sim.press(char)
