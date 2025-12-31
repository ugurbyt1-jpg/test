"""
Metin2 Bot V10.5 - Auto Game Detect
===================================
Yazar: Google Deepmind Agent | Tarih: 2025-12-29

"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import cv2, numpy as np, os, threading, time, json, logging, random, string, secrets
import ctypes
from ctypes import wintypes, Structure, Union, c_long, c_ulong, c_ushort, c_short, POINTER, sizeof, byref
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

try:
    import dxcam as _capture_engine
    import psutil  # YENİ: Otomatik oyun bulma için
    # from pynput import keyboard # KALDIRILDI: Anti-cheat hook tespiti riski
    from ultralytics import YOLO as _DataModel
    from PIL import Image, ImageTk
    import imagehash
    import pytesseract
    
    # YENİ: Input Simulator Entegrasyonu
    from input_simulation import InputSimulator
    input_sim = InputSimulator()
    print(f"[INPUT] ✅ Input Simulator başlatıldı - Mod: {input_sim.mode}")
    
except ImportError as e:
    print(f"[INPUT] ❌ Import error: {e}")
    messagebox.showerror("Error", f"0xE004: Required modules\n{e}")
    input_sim = None
    exit()
except Exception as e:
    print(f"[INPUT] ⚠️ InputSimulator başlatılamadı: {e}")
    input_sim = None

try:
    from m2_captcha import CaptchaSolver
except: pass

# ========== LOW-LEVEL INPUT (Anti-Cheat Bypass) ==========
# InputSimulator Entegrasyonu (Logitech Driver + Humanized Win32)

class LowLevelInput:
    """Anti-cheat bypass: InputSimulator entegrasyonu"""
    
    @staticmethod
    def move_mouse(x, y):
        """InputSimulator ile mouse hareketi"""
        if input_sim:
            input_sim.move_to(x, y)
    
    @staticmethod
    def click(button='left'):
        """InputSimulator ile tıklama"""
        if input_sim:
            input_sim.click(button)
    
    @staticmethod
    def move_relative(dx, dy):
        """Bağıl mouse hareketi"""
        if input_sim:
            x, y = input_sim.get_mouse_pos()
            input_sim.move_to(x + dx, y + dy)

    @staticmethod
    def double_click():
        """Çift tıklama"""
        if input_sim:
            input_sim.double_click()
    
    @staticmethod
    def key_down(key):
        """Tuşa bas"""
        try:
            if input_sim:
                input_sim.key_down(key)
                return True
            else:
                print(f"[INPUT] ⚠️ input_sim yok, key_down({key}) atlandı")
                return False
        except Exception as e:
            print(f"[INPUT] ❌ key_down({key}) hata: {e}")
            return False
    
    @staticmethod
    def key_up(key):
        """Tuşu bırak"""
        try:
            if input_sim:
                input_sim.key_up(key)
                return True
            else:
                print(f"[INPUT] ⚠️ input_sim yok, key_up({key}) atlandı")
                return False
        except Exception as e:
            print(f"[INPUT] ❌ key_up({key}) hata: {e}")
            return False
    
    @staticmethod
    def position():
        """Mouse pozisyonunu al"""
        if input_sim:
            return input_sim.get_mouse_pos()
        return (0, 0)

# ========== LOGGING (Embedded GUI Handler) ==========
class GUILogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            
            last_line = "end-2c linestart"
            end_line = "end-1c"
            
            # Renklendirme Mantığı
            if "HP" in msg or "Can" in msg or "Hasar" in msg:
                self.text_widget.tag_add("hp", last_line, end_line)
                self.text_widget.tag_config("hp", foreground="#ff4d4d") # Kırmızımsı
            elif "REPOSITION" in msg or "Reposition" in msg:
                self.text_widget.tag_add("repo", last_line, end_line)
                self.text_widget.tag_config("repo", foreground="#00ffff") # Turkuaz
            elif "Metin" in msg or "Hedef" in msg or "Target" in msg:
                self.text_widget.tag_add("metin", last_line, end_line)
                self.text_widget.tag_config("metin", foreground="#a0a0a0") # Gri
            elif "✅" in msg or "Başarılı" in msg:
                self.text_widget.tag_add("success", last_line, end_line)
                self.text_widget.tag_config("success", foreground="#00ff00") # Yeşil
            elif "WARNING" in msg or "⚠️" in msg or "SIRAYA" in msg:
                self.text_widget.tag_add("warn", last_line, end_line)
                self.text_widget.tag_config("warn", foreground="orange")
            elif "ERROR" in msg or "❌" in msg:
                self.text_widget.tag_add("err", last_line, end_line)
                self.text_widget.tag_config("err", foreground="red")
        self.text_widget.after(0, append)

logger = logging.getLogger("SysAudioEngine")
logger.setLevel(logging.INFO)

# Anti-Cheat: Rastgele log dosyası ismi
log_filename = f"sys_debug_{secrets.token_hex(4)}.tmp"
logger.addHandler(logging.FileHandler(log_filename))

# ========== CONFIG ==========
class ConfigManager:
    DEFAULT_CONFIG = {
        "pid": 0, "model_path": "", "confidence": 0.50, "attack_timeout": 8.0,
        "verify_timeout": 1.0, "hover_delay": 0.005, "double_click": False,
        "pickup_enabled": True, "pickup_speed": 0.5, "space_mode": "Hasarda Bas",
        "camera_rotation_enabled": True, "camera_rotation_interval": 1.5,
        "camera_rotation_duration": 0.2, "target_bar_region": None,
        "mouse_speed": 0.2,
        "use_human_mouse": True,
        "stuck_detection_enabled": True, "stuck_timeout": 5.0, "stuck_sensitivity": 0.05,
        "bar_lost_timeout": 0.75, "bar_red_min_pixels": 25, "pre_search_enabled": False,
        "damage_verify_timeout": 5.0,
        "hp_stall_detection": False,
        "hp_stall_timeout": 5.0,
        "reposition_enabled": True,
        "reposition_max_attempts": 3,
        "reposition_wait_time": 0.5,
        "reposition_hp_threshold": 10,
        # YENİ: Zoom Out Ayarları
        "zoom_out_enabled": True,
        "zoom_out_on_start": True,
        "zoom_out_interval": 30.0,  # Saniye (0 = sadece başlangıçta)
        "zoom_out_duration": 0.8,   # F tuşu basılı tutma süresi
        "zoom_out_on_no_target": True,  # Hedef bulunamadığında zoom out
        "zoom_out_no_target_interval": 5.0,  # Kaç saniye hedef yoksa zoom out
        # YENİ: Pre-Attack HP Bar Kontrolü
        "pre_attack_hp_check": True,
        "pre_attack_wait_time": 2.0,  # Tıklamadan SONRA bekleme süresi
        "skip_no_bar_targets": True,   # HP bar yoksa hedefi atla
        "failed_target_memory_time": 60.0,  # Failed target hatırlama süresi
        "failed_target_radius": 100,  # Piksel yarıçapı (Artırıldı: 50->100)
        # YENİ: HP Sıçrama Eşiği
        "hp_jump_threshold": 100,  # HP kaç piksel artarsa metin kırıldı sayılsın
        # YENİ: Performans ve Takılma Ayarları
        "fast_mode": False,  # Hızlı Mod (Daha az bekleme, hızlı mouse)
        "aggressive_stuck": True,  # Agresif Takılma Çözümü (180 derece dönüş)
        # YENİ: Anti-Cheat Davranışsal Ayarlar
        "break_enabled": True,
        "break_interval_min": 45.0, # Dakika
        "break_interval_max": 90.0, # Dakika
        "break_duration_min": 3.0,  # Dakika
        "break_duration_max": 12.0, # Dakika
        "human_error_rate": 0.02,   # %2 Hata yapma oranı
        
        # PM / Chat Kontrolü
        "pm_check_enabled": False,
        "pm_check_interval": 5.0,   # Saniye
        "pm_pixel_coords": [100, 500], # Örnek koordinat (x, y) - Kullanıcı ayarlamalı
        "pm_pixel_color": [255, 255, 255], # Beklenen renk (RGB) - Zarf yanıp sönünce değişir
        "pm_action": "stop", # "stop", "alarm", "pause"
    }
    def __init__(self, filename="user_profile.dat"):
        self.filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        self.config = self.load()
    def load(self):
        if not os.path.exists(self.filename): return self.DEFAULT_CONFIG.copy()
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                for k, v in self.DEFAULT_CONFIG.items():
                    if k not in loaded: loaded[k] = v
                return loaded
        except: return self.DEFAULT_CONFIG.copy()
    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except: pass
    def get(self, key, default=None): return self.config.get(key, self.DEFAULT_CONFIG.get(key, default))
    def set(self, key, value): self.config[key] = value

# ========== UTILS ==========
def human_delay(base: float, variance: float = None):
    """Anti-cheat: Gaussian dağılımlı rastgele gecikme
    
    Args:
        base: Temel gecikme süresi (saniye)
        variance: Varyans (None ise base*0.3 kullanılır)
    
    Returns:
        Gaussian dağılımlı rastgele gecikme
    """
    if variance is None:
        variance = base * 0.3
    delay = random.gauss(base, variance)
    
    # Yorgunluk sistemi entegrasyonu
    try:
        if input_sim:
            delay *= input_sim.get_fatigue_multiplier()
    except: pass

    # Negatif değerleri önle, minimum %50, maksimum %200
    return max(base * 0.5, min(base * 2.0, delay))

def generate_random_title():
    """Anti-pattern: XK4721-a3f9c2"""
    letters = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(2))
    numbers = ''.join(secrets.choice(string.digits) for _ in range(4))
    hex_part = secrets.token_hex(3)
    return f"{letters}{numbers}-{hex_part}"

class WinUtils:
    """ctypes tabanlı window işlemleri (WIN32 API yok)"""
    
    # Anti-cheat: Process enumeration cache
    _process_cache = []
    _cache_timestamp = 0
    _cache_ttl = 60  # 1 dakika
    
    # ctypes fonksiyonları
    _user32 = ctypes.windll.user32
    _EnumWindows = _user32.EnumWindows
    _GetWindowRect = _user32.GetWindowRect
    _IsWindowVisible = _user32.IsWindowVisible
    _GetWindowThreadProcessId = _user32.GetWindowThreadProcessId
    _GetWindowTextW = _user32.GetWindowTextW
    _GetWindowTextLengthW = _user32.GetWindowTextLengthW
    _IsIconic = _user32.IsIconic
    _ShowWindow = _user32.ShowWindow
    _SetForegroundWindow = _user32.SetForegroundWindow
    
    # Windows sabitleri
    SW_RESTORE = 9
    
    @staticmethod
    def is_key_pressed(key_code):
        """Anti-cheat safe key check using GetAsyncKeyState"""
        # 0x8000 bit is set if key is down
        return (WinUtils._user32.GetAsyncKeyState(key_code) & 0x8000) != 0

    @staticmethod
    def get_hwnd(pid):
        try:
            hwnds = []
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def enum_cb(hwnd, lparam):
                if WinUtils._user32.IsWindowVisible(hwnd):
                    pid_out = wintypes.DWORD()
                    WinUtils._user32.GetWindowThreadProcessId(hwnd, byref(pid_out))
                    if pid_out.value == pid:
                        hwnds.append(hwnd)
                return True
            WinUtils._EnumWindows(WNDENUMPROC(enum_cb), 0)
            return hwnds[0] if hwnds else None
        except: return None

    @staticmethod
    def get_rect_by_hwnd(hwnd):
        try:
            rect = wintypes.RECT()
            WinUtils._GetWindowRect(hwnd, byref(rect))
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
        except: return None

    @staticmethod
    def get_window_rect(pid): 
        h = WinUtils.get_hwnd(pid)
        return WinUtils.get_rect_by_hwnd(h) if h else None
    
    @staticmethod
    def _get_window_text(hwnd):
        """ctypes ile pencere başlığını al"""
        length = WinUtils._GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        WinUtils._GetWindowTextW(hwnd, buffer, length)
        return buffer.value
    
    @staticmethod
    def is_window_foreground(pid):
        """Belirtilen PID'in penceresi ön planda mı kontrol et"""
        try:
            # Ön plandaki pencere handle'ını al
            foreground_hwnd = WinUtils._user32.GetForegroundWindow()
            if not foreground_hwnd:
                return False
            
            # Ön plandaki pencerenin PID'ini al
            foreground_pid = wintypes.DWORD()
            WinUtils._user32.GetWindowThreadProcessId(foreground_hwnd, byref(foreground_pid))
            
            return foreground_pid.value == pid
        except:
            return False
    
    @staticmethod
    def bring_to_front(pid):
        try:
            hwnds = []
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def enum_cb(hwnd, lparam):
                if WinUtils._user32.IsWindowVisible(hwnd):
                    pid_out = wintypes.DWORD()
                    WinUtils._user32.GetWindowThreadProcessId(hwnd, byref(pid_out))
                    if pid_out.value == pid:
                        hwnds.append(hwnd)
                return True
            WinUtils._EnumWindows(WNDENUMPROC(enum_cb), 0)
            
            if not hwnds: return False
            
            # Pencereyi öne getir
            if WinUtils._IsIconic(hwnds[0]):
                WinUtils._ShowWindow(hwnds[0], WinUtils.SW_RESTORE)
            WinUtils._SetForegroundWindow(hwnds[0])
            
            time.sleep(human_delay(0.3, 0.1))
            return True
        except: return False

    @staticmethod
    def get_metin2_pids():
        """Metin2 oyunlarını otomatik bulur (ctypes tabanlı) - Cache'li"""
        current_time = time.time()
        
        # Cache kontrolü
        if current_time - WinUtils._cache_timestamp < WinUtils._cache_ttl:
            if WinUtils._process_cache:
                return WinUtils._process_cache
        
        # Cache miss - gerçek tarama
        games = []
        # 1. Yöntem: Pencere Başlığına Göre (ctypes)
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_cb(hwnd, lparam):
            if WinUtils._user32.IsWindowVisible(hwnd):
                title = WinUtils._get_window_text(hwnd)
                # Yaygın Metin2 pencere başlıkları
                if "Metin2" in title or "Metin 2" in title or "Gameforge" in title:
                    pid_out = wintypes.DWORD()
                    WinUtils._user32.GetWindowThreadProcessId(hwnd, byref(pid_out))
                    games.append((pid_out.value, title))
            return True
        WinUtils._EnumWindows(WNDENUMPROC(enum_cb), 0)
        
        # 2. Yöntem: Process İsmine Göre (Eğer başlıkta Metin2 yoksa)
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and ('metin2' in proc.info['name'].lower() or 'mt2' in proc.info['name'].lower()):
                    pid = proc.info['pid']
                    # Zaten listede var mı kontrol et
                    if not any(g[0] == pid for g in games):
                        games.append((pid, f"{proc.info['name']} ({pid})"))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Cache'e kaydet
        games = list(set(games))  # Duplicate önle
        WinUtils._process_cache = games
        WinUtils._cache_timestamp = current_time
        
        return games

class RegionSelector:
    def __init__(self, callback):
        self.callback = callback
        self.top = tk.Toplevel()
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)
        self.top.attributes('-topmost', True)
        self.top.configure(bg='black')
        self.canvas = tk.Canvas(self.top, cursor="cross", bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        tk.Label(self.top, text="Select Target Region", font=("Arial", 20), fg="white", bg="red").place(relx=0.5, rely=0.1, anchor="center")
    def on_press(self, e):
        self.sx, self.sy = e.x, e.y
        if hasattr(self, 'rect'): self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.sx, self.sy, self.sx, self.sy, outline="green", width=3)
    def on_drag(self, e):
        self.canvas.coords(self.rect, self.sx, self.sy, e.x, e.y)
    def on_release(self, e):
        x1, x2 = min(self.sx, e.x), max(self.sx, e.x)
        y1, y2 = min(self.sy, e.y), max(self.sy, e.y)
        self.top.destroy()
        if (x2-x1) > 5 and (y2-y1) > 5: self.callback((x1, y1, x2-x1, y2-y1))

# ========== BOT ENGINE ==========
class BotState(Enum):
    IDLE=auto(); SEARCHING=auto(); APPROACHING=auto(); VERIFYING_ATTACK=auto()
    ATTACKING=auto(); RECOVERY=auto(); STUCK_FIX=auto(); ERROR=auto()
    REPOSITIONING_INIT=auto(); REPOSITIONING_MOVE=auto(); REPOSITIONING_FIND=auto()
    REPOSITIONING_WAIT=auto(); REPOSITIONING_CHECK=auto()

@dataclass
class Target:
    pixel_x: int; pixel_y: int; bbox: Tuple[int,int,int,int]
    conf: float; center_offset: int

class MetinBotEngine:
    def __init__(self, cfg, update_ui):
        self.cfg, self.update_ui = cfg, update_ui
        self.running, self.state, self.model, self.pid = False, BotState.IDLE, None, 0
        self.hwnd = None
        self.hwnd_cache_time = 0  # Anti-cheat: HWND cache
        self.hwnd_cache_ttl = 60  # 60 saniye
        self.current_target, self.next_target = None, None
        self.last_state_change, self.last_screenshot = time.time(), None
        self.metin_count, self.bar_lost_start_time = 0, None
        self.last_frame_processed, self.last_move_time = None, time.time()
        self.last_pickup_time, self.stuck_start_time = 0, 0
        self.last_pre_search_time, self.last_pre_search_rotate_time = 0, 0
        self.damage_verified, self.initial_hp_pixels, self.attack_start_time = False, -1, 0
        self.cached_window_rect, self.last_captcha_check_time = None, 0
        self.bar_lost_frame_count = 0
        self.hp_stall_start_time = None
        self.last_hp_for_stall = -1
        self.hp_went_below_threshold = False
        self.min_hp_below_threshold = 9999
        self.last_hp_check = -1
        self.next_target_notified = False
        self.is_initial_search = True
        self.space_held = False
        self.reposition_attempt_count = 0
        self.reposition_initial_hp = -1
        self.failed_targets = []
        self.target_patch = None
        self.target_bbox = None
        self.yolo_frame_counter = 0
        self.stuck_check_counter = 0
        self.rect_poll_counter = 0
        self.start_time = None  # YENİ: İstatistik için başlangıç zamanı
        # YENİ: Zoom Out değişkenleri
        self.last_zoom_out_time = 0
        self.no_target_t_start_time = None # YENİ: T basma zamanlayıcısı
        self.zoom_out_done_on_start = False
        self.no_target_start_time = None
        # YENİ: Pre-Attack HP Check değişkenleri
        self.failed_targets_with_time = []  # [(target, timestamp), ...]
        self.last_failed_clear_time = time.time()
        self.pre_attack_skip_count = 0
        # YENİ: Space tap pattern değişkenleri (Anti-cheat Fix #3)
        self.space_tap_time = 0
        self.space_hold_duration = 0
        self.space_release_time = 0
        # YENİ: 360 Derece Arama ve T Tuşu Mantığı
        self.search_rotation_accumulated = 0.0
        self.search_scan_direction = None
        
        # YENİ: Mola Sistemi (Break System)
        self.last_break_time = time.time()
        self.next_break_interval = random.uniform(
            self.cfg.get("break_interval_min") * 60, 
            self.cfg.get("break_interval_max") * 60
        )
        self.is_on_break = False
        
        # YENİ: PM Kontrolü
        self.last_pm_check_time = 0
        
        try:
            self.camera = _capture_engine.create(output_color="BGR")
            logger.info("Capture init OK")
        except Exception as e:
            logger.error(f"ErrCode 0x2A1: {e}")
            self.camera = None
    
    def set_pid(self, pid): self.pid = pid
    
    def _bezier_curve(self, p0, p1, p2, p3, t):
        """Cubic Bezier eğrisi hesapla"""
        u = 1 - t
        return (
            u*u*u * p0[0] + 3*u*u*t * p1[0] + 3*u*t*t * p2[0] + t*t*t * p3[0],
            u*u*u * p0[1] + 3*u*u*t * p1[1] + 3*u*t*t * p2[1] + t*t*t * p3[1]
        )
    
    def human_move(self, x, y, duration=0.2):
        """Anti-cheat: Gelişmiş Bezier eğrisi + Overshoot + Jitter"""
        start_x, start_y = LowLevelInput.position()
        
        # Mesafeye göre step sayısı ayarla
        dist = ((x - start_x)**2 + (y - start_y)**2)**0.5
        steps = max(12, min(40, int(dist / 10))) # Daha fazla adım
        
        # Overshoot (Hedefi biraz geçip geri gelme)
        if dist > 100 and random.random() < 0.7:
            overshoot_dist = min(30, dist * 0.1)
            angle = np.arctan2(y - start_y, x - start_x)
            x += int(np.cos(angle) * overshoot_dist)
            y += int(np.sin(angle) * overshoot_dist)
            # Overshoot için ekstra adımlar
            steps += 5

        # Rastgele kontrol noktaları oluştur (Bezier eğrisi için)
        mid_x = (start_x + x) / 2
        mid_y = (start_y + y) / 2
        
        # Sapma miktarı mesafeye bağlı
        deviation = min(120, max(30, dist * 0.2))
        
        # İki kontrol noktası - rastgele yönde sapma
        ctrl1 = (
            mid_x + random.uniform(-deviation, deviation) * 0.6,
            mid_y + random.uniform(-deviation, deviation) * 0.6
        )
        ctrl2 = (
            mid_x + random.uniform(-deviation, deviation) * 0.4,
            mid_y + random.uniform(-deviation, deviation) * 0.4
        )
        
        p0 = (start_x, start_y)
        p3 = (x, y)
        
        # Bezier eğrisi boyunca hareket et
        for i in range(steps):
            # Easing: başta ve sonda yavaşla (ease-in-out)
            t = (i + 1) / steps
            t = t * t * (3 - 2 * t)  # Smoothstep easing
            
            bx, by = self._bezier_curve(p0, ctrl1, ctrl2, p3, t)
            
            # Jitter (Titreme)
            if i < steps - 1:
                bx += random.gauss(0, 1.5)
                by += random.gauss(0, 1.5)
            
            LowLevelInput.move_mouse(int(bx), int(by))
            
            # Değişken bekleme süresi
            step_delay = (duration / steps) * random.uniform(0.8, 1.2)
            
            # Micro-stutter (İnsansı takılma) - %5 şansla çok kısa duraksama
            if random.random() < 0.05:
                step_delay += random.uniform(0.01, 0.03)
                
            time.sleep(step_delay)
        
        # Eğer overshoot yapıldıysa, hedefe geri düzeltme hareketi
        if dist > 100 and random.random() < 0.7:
             # Gerçek hedefe küçük bir düzeltme hareketi
             # (Bu fonksiyonun recursive çağrılması yerine basit bir move)
             pass # Şimdilik basit bırakalım, karmaşıklık artmasın
            
    def load_model(self, path):
        try:
            self.update_ui(status="Loading...", color="blue")
            self.model = _DataModel(path)
            try:
                import torch
                if torch.cuda.is_available():
                    self.model.to('cuda')
                    logger.info(f"Model GPU'ya taşındı: {path}")
                else:
                    logger.info(f"Model CPU'da: {path}")
            except:
                logger.info(f"Model CPU'da: {path}")
            self.cfg.set("model_path", path)
            self.update_ui(status="HAZIR", color="green", model_name=os.path.basename(path))
            return True
        except Exception as e:
            logger.error(f"Model fail: {e}")
            return False
    def start(self):
        if not self.model: return messagebox.showerror("Error", "0xE001: Data file required")
        if self.pid == 0: return messagebox.showerror("Error", "0xE002: Process not selected")
        if not self.camera: return messagebox.showerror("Error", "0xE003: Capture init failed")
        self.running = True
        self.start_time = time.time()  # Sayaç başlat
        self.state = BotState.IDLE
        self.is_initial_search = True
        # Zoom out reset
        self.zoom_out_done_on_start = False
        self.last_zoom_out_time = 0
        self.no_target_start_time = None
        # Failed targets reset
        self.failed_targets_with_time = []
        self.pre_attack_skip_count = 0
        self.inference_counter = 0 # Anti-cheat: Saccade counter
        threading.Thread(target=self._run_loop, daemon=True, name="RenderWorker").start()
        logger.info("✅ System started")
    def stop(self):
        self.running = False
        if self.camera: self.camera.stop()
        self.update_ui(status="DURDUR", color="red")
    def reset_counter(self):
        self.metin_count = 0
        self.update_ui(metin_count=0)
        logger.info("📊 Sayaç sıfırlandı")
    
    def _transition(self, new_state):
        prev = self.state
        if prev == BotState.ATTACKING and self.space_held:
            LowLevelInput.key_up('space')
            self.space_held = False
        self.state = new_state
        self.last_state_change = time.time()
        if new_state not in [BotState.APPROACHING, BotState.SEARCHING]: self.stuck_start_time = 0
        self.bar_lost_start_time = None
        if new_state == BotState.SEARCHING:
            # Arama moduna girince rotasyon sayacını sıfırla
            self.search_rotation_accumulated = 0.0
            self.search_scan_direction = None
        
        if new_state == BotState.ATTACKING:
            self.damage_verified = False
            self.initial_hp_pixels = -1
            self.attack_start_time = 0
            self.bar_lost_frame_count = 0
            self.hp_went_below_threshold = False
            self.min_hp_below_threshold = 9999
            self.next_target_notified = False
            self.last_hp_for_stall = -1
            self.hp_stall_start_time = None
            self.space_held = False
        logger.info(f"{prev.name} → {new_state.name}")
        status_map = {
            BotState.SEARCHING: ("🔍 Aranıyor", "blue"),
            BotState.APPROACHING: ("🎯 Gidiliyor", "orange"),
            BotState.VERIFYING_ATTACK: ("👀 Doğrula", "purple"),
            BotState.ATTACKING: ("⚔️ SALDIRI", "red"),
            BotState.STUCK_FIX: ("🛑 TAKILMA", "magenta"),
            BotState.REPOSITIONING_INIT: ("🔄 REP.INIT", "cyan"),
            BotState.REPOSITIONING_MOVE: ("🔄 REP.MOVE", "cyan"),
            BotState.REPOSITIONING_FIND: ("🔄 REP.FIND", "cyan"),
            BotState.REPOSITIONING_WAIT: ("🔄 REP.WAIT", "cyan"),
            BotState.REPOSITIONING_CHECK: ("🔄 REP.CHK", "cyan"),
            BotState.IDLE: ("Bekliyor", "black")
        }
        text, color = status_map.get(new_state, (new_state.name, "black"))
        self.update_ui(status=text, color=color, metin_count=self.metin_count)
    def _check_stuck(self, frame):
        if not self.cfg.get("stuck_detection_enabled"): return False
        if self.state not in [BotState.SEARCHING, BotState.APPROACHING]: return False
        if self.last_frame_processed is None:
            self.last_frame_processed, self.last_move_time = frame, time.time()
            return False
        try:
            sc, sl = cv2.resize(frame, (64,64)), cv2.resize(self.last_frame_processed, (64,64))
            diff = cv2.absdiff(cv2.cvtColor(sc, cv2.COLOR_BGR2GRAY), cv2.cvtColor(sl, cv2.COLOR_BGR2GRAY))
            ratio = np.count_nonzero(diff > 15) / (64*64)
            if ratio > self.cfg.get("stuck_sensitivity"):
                self.last_frame_processed, self.last_move_time = frame, time.time()
                return False
            elapsed = time.time() - self.last_move_time
            if elapsed > self.cfg.get("stuck_timeout"):
                logger.warning(f"⚠️ Stuck {elapsed:.1f}s")
                return True
        except: pass
        return False
    def _do_zoom_out(self, reason=""):
        """F tuşu ile zoom out yap - Anti-cheat: LowLevelInput"""
        duration = float(self.cfg.get("zoom_out_duration"))
        LowLevelInput.key_down('f')
        time.sleep(duration)
        LowLevelInput.key_up('f')
        self.last_zoom_out_time = time.time()
        logger.info(f"🔭 Zoom Out yapıldı ({duration:.1f}s) {reason}")
    
    def _clean_failed_targets(self):
        """Eski failed targetları temizle"""
        memory_time = float(self.cfg.get("failed_target_memory_time"))
        current_time = time.time()
        self.failed_targets_with_time = [
            (t, ts) for t, ts in self.failed_targets_with_time 
            if current_time - ts < memory_time
        ]
    
    def _is_target_failed(self, target):
        """Bu hedef daha önce başarısız oldu mu?"""
        radius = int(self.cfg.get("failed_target_radius"))
        for failed_target, _ in self.failed_targets_with_time:
            dist = ((target.pixel_x - failed_target.pixel_x)**2 + 
                    (target.pixel_y - failed_target.pixel_y)**2)**0.5
            if dist < radius:
                return True
        return False
    
    def _add_failed_target(self, target):
        """Hedefi failed listesine ekle"""
        self.failed_targets_with_time.append((target, time.time()))
        self.pre_attack_skip_count += 1
        logger.warning(f"🚫 Hedef failed listesine eklendi (Toplam skip: {self.pre_attack_skip_count})")

    def _take_break(self):
        """Anti-cheat: İnsansı mola ver"""
        if not self.cfg.get("break_enabled"): return
        
        duration = random.uniform(
            self.cfg.get("break_duration_min") * 60,
            self.cfg.get("break_duration_max") * 60
        )
        logger.info(f"☕ MOLA ZAMANI! {duration/60:.1f} dakika dinleniliyor...")
        self.update_ui(status=f"☕ MOLA ({int(duration)}s)", color="brown")
        self.is_on_break = True
        
        # Mola sırasında botu durdurma, sadece bekle
        start_break = time.time()
        while time.time() - start_break < duration and self.running:
            remaining = int(duration - (time.time() - start_break))
            if remaining % 10 == 0:
                self.update_ui(status=f"☕ MOLA ({remaining}s)", color="brown")
            time.sleep(1)
            
        self.last_break_time = time.time()
        self.next_break_interval = random.uniform(
            self.cfg.get("break_interval_min") * 60, 
            self.cfg.get("break_interval_max") * 60
        )
        self.is_on_break = False
        logger.info(f"☕ Mola bitti. Sonraki mola: {self.next_break_interval/60:.1f} dk sonra")
        self.update_ui(status="Mola Bitti", color="green")

    def _check_pm(self, frame):
        """PM Kontrolü - Belirtilen piksel değiştiyse işlem yap"""
        if not self.cfg.get("pm_check_enabled"): return False
        
        # Anti-cheat: Kontrol aralığına rastgelelik ekle (+- %20)
        interval = float(self.cfg.get("pm_check_interval"))
        interval = interval * random.uniform(0.8, 1.2)
        
        if time.time() - self.last_pm_check_time < interval:
            return False
        self.last_pm_check_time = time.time()
        
        coords = self.cfg.get("pm_pixel_coords") # [x, y]
        target_color = self.cfg.get("pm_pixel_color") # [r, g, b]
        
        if not coords or not target_color: return False
        
        try:
            # Frame içindeki pikseli kontrol et
            # Not: frame BGR formatında olabilir, target_color RGB ise dönüşüm gerekebilir
            # frame shape: (h, w, 3)
            x, y = coords
            if y >= frame.shape[0] or x >= frame.shape[1]: return False
            
            pixel = frame[y, x] # BGR
            # Basit renk farkı kontrolü (Euclidean distance)
            # target_color (RGB) -> BGR'ye çevirip karşılaştırabiliriz veya tam tersi
            target_bgr = target_color[::-1] 
            
            dist = np.sqrt(np.sum((pixel - target_bgr)**2))
            
            if dist < 30: # Renk eşleşti (Toleranslı)
                action = self.cfg.get("pm_action")
                logger.warning(f"📩 PM TESPİT EDİLDİ! Aksiyon: {action}")
                
                if action == "stop":
                    self.stop()
                    # Thread içinde messagebox sorun olabilir ama deneyelim
                    # messagebox.showwarning("PM Tespit", "Gelen mesaj algılandı, bot durduruldu.")
                    return True
                elif action == "alarm":
                    import winsound
                    winsound.Beep(1000, 1000)
                elif action == "pause":
                    time.sleep(60) # 1 dk bekle
                    
        except Exception as e:
            logger.error(f"PM Check Error: {e}")
            
        return False
    
    def _run_loop(self):
        self.camera.start(target_fps=60)
        
        # Başlangıçta Zoom Out
        if self.cfg.get("zoom_out_enabled") and self.cfg.get("zoom_out_on_start"):
            time.sleep(human_delay(0.5, 0.15))  # Oyun penceresinin hazır olmasını bekle
            self._do_zoom_out("[Başlangıç]")
            self.zoom_out_done_on_start = True
        
        while self.running:
            try:
                # Periyodik failed target temizliği
                if time.time() - self.last_failed_clear_time > 10:
                    self._clean_failed_targets()
                    self.last_failed_clear_time = time.time()
                
                # Periyodik Zoom Out (interval > 0 ise)
                zoom_interval = float(self.cfg.get("zoom_out_interval"))
                if self.cfg.get("zoom_out_enabled") and zoom_interval > 0:
                    if time.time() - self.last_zoom_out_time > zoom_interval:
                        self._do_zoom_out("[Periyodik]")
                
                # Anti-cheat: HWND Cache Sistemi (60 saniye)
                if not self.hwnd or (time.time() - self.hwnd_cache_time) > self.hwnd_cache_ttl:
                    self.hwnd = WinUtils.get_hwnd(self.pid)
                    self.hwnd_cache_time = time.time()
                    if not self.hwnd:
                        self.update_ui(status="Window?", color="red")
                        time.sleep(1)
                        continue
                        
                rect = WinUtils.get_rect_by_hwnd(self.hwnd)
                if not rect:
                    self.hwnd = None
                    self.update_ui(status="Pencere?", color="red")
                    time.sleep(1)
                    continue
                wx, wy, ww, wh = rect
                self.cached_window_rect = rect
                frame = self.camera.get_latest_frame()
                if frame is None: time.sleep(0.01); continue
                try: self.last_screenshot = frame[wy:wy+wh, wx:wx+ww]
                except: time.sleep(0.1); continue
                
                # YENİ: PM Kontrolü (Chat/PM Control)
                if self._check_pm(self.last_screenshot): 
                    break # Stop loop if PM detected and action is stop

                # YENİ: Mola Kontrolü (Break System)
                if time.time() - self.last_break_time > self.next_break_interval:
                    self._take_break()

                if self._check_stuck(self.last_screenshot): self._transition(BotState.STUCK_FIX)
                self._handle_loot()
                if self.state == BotState.IDLE: self._transition(BotState.SEARCHING)
                elif self.state == BotState.SEARCHING: 
                    if self._handle_searching(ww, wh, wx, wy): continue
                elif self.state == BotState.APPROACHING: self._handle_approaching(wx, wy)
                elif self.state == BotState.VERIFYING_ATTACK: self._handle_verifying()
                elif self.state == BotState.ATTACKING: self._handle_attacking()
                elif self.state == BotState.RECOVERY: self._handle_recovery()
                elif self.state == BotState.STUCK_FIX: self._handle_stuck_fix()
                elif self.state == BotState.REPOSITIONING_INIT: self._handle_repositioning_init()
                elif self.state == BotState.REPOSITIONING_MOVE: self._handle_repositioning_move()
                elif self.state == BotState.REPOSITIONING_FIND: self._handle_repositioning_find()
                elif self.state == BotState.REPOSITIONING_WAIT: self._handle_repositioning_wait()
                elif self.state == BotState.REPOSITIONING_CHECK: self._handle_repositioning_check()
                self.update_ui()
                
                # Anti-cheat: Loop hızını randomize et + Lag Spike Simülasyonu
                if random.random() < 0.01: # %1 ihtimalle lag spike
                    time.sleep(random.uniform(0.1, 0.3))
                else:
                    time.sleep(random.uniform(0.02, 0.06))
            except Exception as e:
                logger.error(f"ErrCode: {random.randint(1000,9999)}")
                logger.error(f"Loop: {e}")
                time.sleep(1)
    def _do_t_press_action(self, reason=""):
        """360 derece dönüş sonrası veya uzun süre hedef bulunamazsa T tuşuna bas"""
        logger.info(f"🔄 T tuşuna basılıyor (2sn)... {reason}")
        self.update_ui(status="T BASILIYOR", color="magenta")
        
        LowLevelInput.key_down('t')
        time.sleep(human_delay(2.0))
        LowLevelInput.key_up('t')
        
        # T işleminden sonra biraz bekle ve yön değiştir
        time.sleep(human_delay(0.5))
        self.search_rotation_accumulated = 0.0
        # Yönü tersine çevir
        if self.search_scan_direction:
            self.search_scan_direction = 'e' if self.search_scan_direction == 'q' else 'q'
        
        self.update_ui(status="🔍 Aranıyor", color="blue")
# Anti-cheat: Saccade Simülasyonu (Her frame'de bakma)
        self.inference_counter += 1
        if self.inference_counter % random.randint(2, 4) != 0:
            return

        
    def _handle_searching(self, ww, wh, wx=0, wy=0):
        results = self.model.predict(source=self.last_screenshot, conf=self.cfg.get("confidence"), verbose=False, device='cpu')
        candidates, cx, cy = [], ww//2, wh//2
        if len(results) > 0 and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                tcx, tcy = (x1+x2)//2, (y1+y2)//2
                dist = ((tcx-cx)**2 + (tcy-cy)**2)**0.5
                if dist < 30 or x1 < 5 or y1 < 5 or x2 > ww-5 or y2 > wh-5: continue
                candidates.append(Target(tcx, tcy, (x1,y1,x2,y2), float(box.conf[0]), dist))
        
        # YENİ: Failed target filtreleme
        if candidates and self.cfg.get("skip_no_bar_targets"):
            valid_candidates = [c for c in candidates if not self._is_target_failed(c)]
            if len(valid_candidates) < len(candidates):
                skipped = len(candidates) - len(valid_candidates)
                logger.info(f"🔄 {skipped} hedef atlandı (failed list)")
            candidates = valid_candidates
        
        if candidates:
            candidates.sort(key=lambda t: t.center_offset)
            self.current_target = candidates[0]
            self.is_initial_search = False
            self.no_target_start_time = None  # Hedef bulundu, reset
            self.no_target_t_start_time = None # Hedef bulundu, T timer reset
            self.search_rotation_accumulated = 0.0 # Hedef bulundu, rotasyon sayacını sıfırla
            self._transition(BotState.APPROACHING)
            if wx > 0 and wy > 0: self._handle_approaching(wx, wy)
            return True
        else:
            # YENİ: Hedef bulunamadı - T Tuşu Kontrolü (5sn)
            if self.no_target_t_start_time is None:
                self.no_target_t_start_time = time.time()
            
            if time.time() - self.no_target_t_start_time > 5.0:
                self._do_t_press_action("[10sn Hedef Yok]")
                self.no_target_t_start_time = time.time() # Reset timer
                return False

            # YENİ: Hedef bulunamadı - Zoom Out tetikle
            if self.cfg.get("zoom_out_enabled") and self.cfg.get("zoom_out_on_no_target"):
                if self.no_target_start_time is None:
                    self.no_target_start_time = time.time()
                else:
                    no_target_elapsed = time.time() - self.no_target_start_time
                    no_target_interval = float(self.cfg.get("zoom_out_no_target_interval"))
                    if no_target_elapsed >= no_target_interval:
                        self._do_zoom_out(f"[Hedef Yok {no_target_elapsed:.1f}s]")
                        self.no_target_start_time = time.time()  # Reset timer
            
            should_rotate = False
            if self.cfg.get("camera_rotation_enabled"):
                interval = float(self.cfg.get("camera_rotation_interval"))
                if self.cfg.get("fast_mode"): interval = min(0.2, interval)
                search_interval = min(0.5, interval)
                
                if self.is_initial_search:
                    should_rotate = True
                    self.is_initial_search = False
                    logger.info("🚀 Hızlı Başlangıç: Hemen kamera çevriliyor...")
                elif time.time() - self.last_state_change > search_interval:
                    should_rotate = True
            if should_rotate:
                # YENİ: Tutarlı yön ile tarama
                if not self.search_scan_direction:
                    self.search_scan_direction = random.choice(['q', 'e'])
                
                dur = self._rotate_camera(force_direction=self.search_scan_direction)
                self.search_rotation_accumulated += dur
                self.last_state_change = time.time()
                
                # 360 Derece kontrolü (Yaklaşık 3.5 saniye tam tur kabul edelim)
                if self.search_rotation_accumulated > 3.5:
                    self._do_t_press_action("[360° Tarama]")
                    
            return False
    def _handle_approaching(self, wx, wy):
        """Anti-cheat Fix #7: Rastgele offset ve micro delay ile tıklama"""
        if not self.current_target: return self._transition(BotState.SEARCHING)
        tx, ty = self.current_target.pixel_x, self.current_target.pixel_y
        
        # YENİ: İnsansı Hata (Human Error)
        # Bazen yanlış yere tıkla veya hedefi ıskala
        if random.random() < self.cfg.get("human_error_rate", 0.02):
            logger.info("🤷 İnsansı hata yapılıyor (Iskalama)...")
            # Hedefin biraz uzağına tıkla
            error_x = random.choice([-1, 1]) * random.randint(30, 80)
            error_y = random.choice([-1, 1]) * random.randint(30, 80)
            
            target_x = wx + tx + error_x
            target_y = wy + ty + error_y
            
            if self.cfg.get("use_human_mouse"):
                self.human_move(target_x, target_y, duration=0.3)
            else:
                LowLevelInput.move_mouse(target_x, target_y)
                
            LowLevelInput.click()
            time.sleep(random.uniform(0.2, 0.5)) # Hatayı fark etme süresi
            return # Bu döngüyü pas geç, bir sonraki döngüde tekrar deneyecek
        
        # Fix #7: Daha geniş ve Gaussian dağılımlı offset
        offset_x = int(random.gauss(0, 4))  # σ=4 piksel
        offset_y = int(random.gauss(0, 4))
        # Maksimum ±10 piksel sınırla
        offset_x = max(-10, min(10, offset_x))
        offset_y = max(-10, min(10, offset_y))
        
        try:
            target_x = wx + tx + offset_x
            target_y = wy + ty + offset_y
            
            # 1️⃣ Mouse'u hedefe götür
            if self.cfg.get("use_human_mouse"):
                base_speed = float(self.cfg.get("mouse_speed"))
                if self.cfg.get("fast_mode"): base_speed *= 0.5  # Hızlı Mod: %50 daha hızlı mouse
                duration = (base_speed * 0.5) * random.uniform(0.8, 1.2)
                self.human_move(target_x, target_y, duration=duration)
            else:
                LowLevelInput.move_mouse(target_x, target_y)
            
            # Fix #7: Micro delay before click (insansı tepki süresi)
            delay_before_click = random.uniform(0.03, 0.12)
            if self.cfg.get("fast_mode"): delay_before_click *= 0.5
            time.sleep(delay_before_click)
            
            # 2️⃣ TIKLA (Metini seç) - Anti-cheat: LowLevelInput
            hover = self.cfg.get("hover_delay")
            if self.cfg.get("fast_mode"): hover = 0
            if hover > 0: time.sleep(human_delay(hover, hover * 0.3))
            if self.cfg.get("double_click"):
                LowLevelInput.double_click()
            else:
                LowLevelInput.click()
            
            # ====== YENİ: PRE-ATTACK HP BAR KONTROLÜ (Tiklama SONRASI) ======
            if self.cfg.get("pre_attack_hp_check") and self.cfg.get("target_bar_region"):
                wait_time = float(self.cfg.get("pre_attack_wait_time"))
                actual_wait = human_delay(wait_time, wait_time * 0.25)
                logger.info(f"🔍 Pre-Attack: {actual_wait:.2f}s bekleniyor (HP bar kontrolü)...")
                time.sleep(actual_wait)
                
                # Yeni frame al
                try:
                    frame = self.camera.get_latest_frame()
                    if frame is not None:
                        rect = WinUtils.get_rect_by_hwnd(self.hwnd)
                        if rect:
                            rwx, rwy, rww, rwh = rect
                            self.last_screenshot = frame[rwy:rwy+rwh, rwx:rwx+rww]
                            self.cached_window_rect = rect
                except: pass
                
                px = self._get_target_bar_pixels()
                threshold = int(self.cfg.get("bar_red_min_pixels"))
                
                if px < threshold:
                    # HP bar görünmüyor - hedef seçilemedi
                    logger.warning(f"⚠️ Pre-Attack: HP bar YOK ({px}px < {threshold}px) - Hedef atlanıyor!")
                    if self.cfg.get("skip_no_bar_targets"):
                        self._add_failed_target(self.current_target)
                        self.current_target = None
                        self._transition(BotState.SEARCHING)
                        return
                else:
                    logger.info(f"✅ Pre-Attack: HP bar ALGILANDI ({px}px) - Hasar doğrulamasına geçiliyor...")
            # ====== PRE-ATTACK SONU ======
            
        except Exception as e:
            logger.error(f"Approaching error: {e}")
        self.next_target = None
        self._transition(BotState.VERIFYING_ATTACK)
    def _handle_verifying(self):
        if self._get_target_bar_pixels() > int(self.cfg.get("bar_red_min_pixels")):
            self._transition(BotState.ATTACKING)
            return
        if time.time() - self.last_state_change > self.cfg.get("verify_timeout"):
            # YENİ: Timeout olduysa hedefi failed listesine ekle (Su/Engel durumunda loop'u önler)
            if self.current_target:
                logger.warning(f"⚠️ Hedefe ulaşılamadı (Verify Timeout) - Hedef engelleniyor...")
                self._add_failed_target(self.current_target)
            self._transition(BotState.SEARCHING)
    def _get_target_bar_pixels(self):
        region = self.cfg.get("target_bar_region")
        if not region: return 9999
        try:
            if not self.cached_window_rect: return 0
            wx, wy, ww, wh = self.cached_window_rect
            rx, ry, rw, rh = region
            lx, ly = rx-wx, ry-wy
            if lx < 0 or ly < 0 or lx+rw > ww or ly+rh > wh: return 0
            roi = self.last_screenshot[ly:ly+rh, lx:lx+rw]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
            mask1 = (h >= 0) & (h <= 15) & (s >= 50) & (s <= 255) & (v >= 50) & (v <= 255)
            mask2 = (h >= 160) & (h <= 180) & (s >= 50) & (s <= 255) & (v >= 50) & (v <= 255)
            combined_mask = mask1 | mask2
            return int(np.sum(combined_mask))
        except: return 0
    def _is_bar_truly_lost(self, px):
        if px > 0:
            self.bar_lost_frame_count = 0
            return False
        self.bar_lost_frame_count += 1
        return self.bar_lost_frame_count >= 3
    def _transition_from_attack(self):
        if self.next_target:
            logger.info("→ Sıradaki hedefe geçiliyor")
            self.current_target, self.next_target = self.next_target, None
            self._transition(BotState.APPROACHING)
        else:
            self._transition(BotState.SEARCHING)
    def _handle_attacking(self):
        ct, px = time.time(), self._get_target_bar_pixels()
        has_bar, limit = self.cfg.get("target_bar_region") is not None, self.cfg.get("attack_timeout")
        space_mode = self.cfg.get("space_mode")
        
        # Anti-cheat Fix #3: Space tap-release pattern
        if space_mode == "Daima Basılı Tut":
            self._manage_space_tap(ct)
        if not self.damage_verified and has_bar:
            if self.initial_hp_pixels == -1 and (ct - self.last_state_change) > 0.5:
                self.initial_hp_pixels = px
                logger.info(f"⚜️ Attack Init Px: {self.initial_hp_pixels}")
            trigger = max(0, int(self.initial_hp_pixels * 0.95)) if self.initial_hp_pixels > 0 else 0
            verify_timeout = float(self.cfg.get("damage_verify_timeout"))
            if px < trigger and self.initial_hp_pixels > 0:
                diff = self.initial_hp_pixels - px
                self.damage_verified, self.attack_start_time = True, ct
                logger.info(f"✅ Hasar: {self.initial_hp_pixels}→{px} (-{diff}px, %{(diff/self.initial_hp_pixels)*100:.1f})")
                self.last_hp_check = px
                if space_mode == "Hasarda Bas" and not self.space_held:
                    LowLevelInput.key_down('space')
                    self.space_held = True
            else:
                elapsed = ct - self.last_state_change
                self.update_ui(info=f"Hasar?: {verify_timeout-elapsed:.1f}s | HP: {px}px (Trigger: {trigger}px)")
                if elapsed > verify_timeout:
                    if self.cfg.get("reposition_enabled"):
                        logger.warning(f"⚠️ {verify_timeout}s hasar yok, REPOSITION başlatılıyor...")
                        self._transition(BotState.REPOSITIONING_INIT)
                        return
                    else:
                        logger.warning(f"⚠️ {verify_timeout}s hasar yok, minimal hareket + retarget!")
                        if self.space_held:
                            LowLevelInput.key_up('space')
                            self.space_held = False
                        side_key = random.choice(['a', 'd'])
                        LowLevelInput.key_down(side_key); time.sleep(human_delay(0.2)); LowLevelInput.key_up(side_key)
                        LowLevelInput.key_down('s'); time.sleep(human_delay(0.4)); LowLevelInput.key_up('s')
                        if self.cfg.get("camera_rotation_enabled"):
                            rot_key = random.choice(['q', 'e'])
                            LowLevelInput.key_down(rot_key); time.sleep(human_delay(0.15)); LowLevelInput.key_up(rot_key)
                        logger.info("🔄 Minimal hareket yapıldı, yeni hedef aranıyor...")
                        self._transition(BotState.SEARCHING)
                        return
                self._check_bar_lost(px)
                return
        if self.attack_start_time == 0: self.attack_start_time = self.last_state_change
        elapsed = ct - self.attack_start_time
        self.update_ui(info=f"⚔️ {max(0, limit-elapsed):.1f}s | HP: {px}px")
        if self.cfg.get("hp_stall_detection") and has_bar and self.damage_verified:
            if self.last_hp_for_stall == -1:
                self.last_hp_for_stall = px
                self.hp_stall_start_time = ct
            else:
                hp_diff = self.last_hp_for_stall - px
                if hp_diff > 3:
                    logger.info(f"💚 HP azalıyor: {self.last_hp_for_stall}→{px} (-{hp_diff}px)")
                    self.last_hp_for_stall = px
                    self.hp_stall_start_time = ct
                elif hp_diff < -3:
                    logger.warning(f"⚠️ HP arttı? {self.last_hp_for_stall}→{px} (+{abs(hp_diff)}px)")
                    if abs(hp_diff) > 200:
                        logger.info(f"💀 Metin kırıldı (HP sıçraması algılandı: +{abs(hp_diff)}px)")
                        self.metin_count += 1
                        self._transition_from_attack()
                        return
                    self.last_hp_for_stall = px
                    self.hp_stall_start_time = ct
                else:
                    stall_elapsed = ct - self.hp_stall_start_time
                    stall_timeout = float(self.cfg.get("hp_stall_timeout"))
                    if stall_elapsed > stall_timeout:
                        logger.warning(f"🛑 HP {stall_timeout}s durdu, stuck fix + retarget!")
                        for k, d in [('s', 1.0), ('q', 0.5), (random.choice(['a','d']), 0.5)]:
                            LowLevelInput.key_down(k); time.sleep(d); LowLevelInput.key_up(k)
                        self.hp_stall_start_time = None
                        self.last_hp_for_stall = -1
                        self._transition(BotState.SEARCHING)
                        return
        if self.cfg.get("pre_search_enabled") and ct - self.last_pre_search_time > 0.5:
            self.last_pre_search_time = ct
            self._do_pre_search()
        if (has_bar and elapsed > 30) or (not has_bar and elapsed > limit):
            self._transition_from_attack()
            return
        self._check_bar_lost(px)
    
    def _manage_space_tap(self, ct):
        """Anti-cheat Fix #3: Space tuşunu tap-release pattern ile yönet - LowLevelInput"""
        if not self.space_held:
            # Space basılı değil - basma zamanı geldi mi?
            if ct - self.space_release_time >= random.uniform(0.08, 0.25):
                LowLevelInput.key_down('space')
                self.space_held = True
                self.space_tap_time = ct
                self.space_hold_duration = random.uniform(2.0, 4.5)  # 2-4.5 saniye basılı tut
        else:
            # Space basılı - bırakma zamanı geldi mi?
            if ct - self.space_tap_time >= self.space_hold_duration:
                LowLevelInput.key_up('space')
                self.space_held = False
                self.space_release_time = ct
    
    def _handle_loot(self):
        """Anti-cheat Fix #4: Yavaşlatılmış ve insansı loot toplama - LowLevelInput"""
        if self.cfg.get("pickup_enabled"):
            # Sadece oyun penceresi ön plandayken topla
            if not WinUtils.is_window_foreground(self.pid):
                return
            
            ct = time.time()
            base_spd = float(self.cfg.get("pickup_speed"))
            # Fix #4: Daha uzun ve rastgele interval (2-5 saniye arası)
            min_interval = max(2.0, base_spd)
            max_interval = min_interval + random.uniform(1.5, 3.0)
            interval = random.uniform(min_interval, max_interval)
            if ct - self.last_pickup_time >= interval:
                # Rastgele micro delay ekle
                time.sleep(random.uniform(0.02, 0.08))
                hold_duration = random.uniform(0.08, 0.20)
                LowLevelInput.key_down('`')
                time.sleep(hold_duration)
                LowLevelInput.key_up('`')
                self.last_pickup_time = ct
    def _check_bar_lost(self, px):
        if not self.cfg.get("target_bar_region"): return
        threshold = int(self.cfg.get("bar_red_min_pixels"))
        if px > 0 and px < threshold:
            self.hp_went_below_threshold = True
            if px < self.min_hp_below_threshold:
                self.min_hp_below_threshold = px
        if self.hp_went_below_threshold:
            hp_jump_threshold = int(self.cfg.get("hp_jump_threshold"))
            if px >= threshold or (px - self.min_hp_below_threshold) > hp_jump_threshold:
                logger.info(f"💀 Metin kırıldı (HP sıçraması: {self.min_hp_below_threshold}px -> {px}px, eşik: {hp_jump_threshold}px)")
                if self.space_held:
                    LowLevelInput.key_up('space')
                    self.space_held = False
                self.metin_count += 1
                self.hp_went_below_threshold = False
                self.min_hp_below_threshold = 9999
                self._transition_from_attack()
                return
        if px == 0:
            if self.bar_lost_start_time is None: 
                self.bar_lost_start_time = time.time()
            elapsed = time.time() - self.bar_lost_start_time
            timeout = 0.1 if self.next_target else float(self.cfg.get("bar_lost_timeout"))
            if elapsed >= timeout:
                logger.info("💀 Metin kırıldı (bar kayboldu)")
                if self.space_held:
                    LowLevelInput.key_up('space')
                    self.space_held = False
                self.metin_count += 1
                self.bar_lost_start_time = None
                self._transition_from_attack()
        elif px > 0 and px < threshold:
            if self.bar_lost_start_time is None:
                self.bar_lost_start_time = time.time()
                logger.info(f"⚠️ HP kritik seviyede ({px}px < {threshold}px)")
            elapsed = time.time() - self.bar_lost_start_time
            if elapsed >= 0.3:
                logger.info(f"💀 Metin kırıldı (HP eşik altında {elapsed:.1f}s)")
                if self.space_held:
                    LowLevelInput.key_up('space')
                    self.space_held = False
                self.metin_count += 1
                self.bar_lost_start_time = None
                self._transition_from_attack()
        else:
            self.bar_lost_start_time = None
    def _do_pre_search(self):
        try:
            res = self.model.predict(source=self.last_screenshot, conf=self.cfg.get("confidence"), verbose=False, device='cpu')
            cands, h, w = [], self.last_screenshot.shape[0], self.last_screenshot.shape[1]
            cx, cy = w//2, h//2
            if len(res) > 0 and len(res[0].boxes) > 0:
                for box in res[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    tcx, tcy = (x1+x2)//2, (y1+y2)//2
                    dist = ((tcx-cx)**2 + (tcy-cy)**2)**0.5
                    if dist < 60 or x1 < 5 or y1 < 5 or x2 > w-5 or y2 > h-5: continue
                    cands.append(Target(tcx, tcy, (x1,y1,x2,y2), float(box.conf[0]), dist))
            if cands:
                cands.sort(key=lambda t: t.center_offset)
                self.next_target = cands[0]
                if not self.next_target_notified:
                    logger.warning(f"⚡ SIRAYA EKLENDİ | Toplam: {len(cands)} | En yakın: {cands[0].center_offset:.0f}px")
                    self.next_target_notified = True
            else:
                self.next_target = None
                if self.cfg.get("camera_rotation_enabled") and time.time() - self.last_pre_search_rotate_time > self.cfg.get("camera_rotation_interval"):
                    self._rotate_camera()
                    self.last_pre_search_rotate_time = time.time()
        except: pass
    def _handle_stuck_fix(self):
        """Anti-cheat Fix #5: Rastgele kombinasyonlarla stuck fix - LowLevelInput"""
        logger.info("🛑 Stuck fix...")
        
        if self.cfg.get("aggressive_stuck"):
            # Agresif Mod: 180 derece dön ve uzaklaş
            logger.info("🔄 Agresif Stuck Fix: 180° Dönüş + Kaçış")
            rot_key = random.choice(['q', 'e'])
            LowLevelInput.key_down(rot_key)
            time.sleep(human_delay(1.6)) # Yaklaşık 180 derece
            LowLevelInput.key_up(rot_key)
            
            LowLevelInput.key_down('w')
            time.sleep(human_delay(1.5)) # Uzun koşu
            LowLevelInput.key_up('w')
        else:
            # Fix #5: Rastgele hareket kombinasyonu seç
            patterns = [
                [('s', 1.2), ('q', 0.6), ('a', 0.4)],
                [('w', 0.8), ('e', 0.5), ('d', 0.6), ('s', 0.3)],
                [('a', 1.0), ('s', 0.7), ('q', 0.4)],
                [('d', 0.9), ('s', 0.8), ('e', 0.5)],
                [('s', 1.5), ('a', 0.4), ('q', 0.3), ('d', 0.4)],
                [('w', 0.5), ('q', 0.8), ('s', 1.0)],
            ]
            chosen_pattern = random.choice(patterns)
            
            for k, d in chosen_pattern:
                # Rastgele micro delay
                time.sleep(random.uniform(0.02, 0.1))
                actual_duration = human_delay(d, d * 0.35)
                LowLevelInput.key_down(k)
                time.sleep(actual_duration)
                LowLevelInput.key_up(k)
        
        self.last_move_time, self.last_frame_processed = time.time(), None
        self._transition(BotState.SEARCHING)
    def _handle_recovery(self): self._handle_stuck_fix()
    def _handle_repositioning_init(self):
        logger.info("🔄 REPOSITION: Init - HP ve hedef görüntüsü kaydediliyor...")
        self.failed_targets = []
        px = self._get_target_bar_pixels()
        self.reposition_initial_hp = px
        logger.info(f"📊 Reposition başlangıç HP: {px}px")
        if self.current_target and self.last_screenshot is not None:
            try:
                x1, y1, x2, y2 = self.current_target.bbox
                h, w = self.last_screenshot.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                if x2 > x1 and y2 > y1:
                    self.target_patch = self.last_screenshot[y1:y2, x1:x2].copy()
                    self.target_bbox = (x1, y1, x2, y2)
                    logger.info(f"📸 Hedef görüntüsü kaydedildi: {x2-x1}x{y2-y1}px")
                else:
                    self.target_patch = None
                    self.target_bbox = None
            except Exception as e:
                logger.warning(f"⚠️ Hedef görüntüsü kaydedilemedi: {e}")
                self.target_patch = None
                self.target_bbox = None
        else:
            self.target_patch = None
            self.target_bbox = None
        if self.space_held:
            LowLevelInput.key_up('space')
            self.space_held = False
        self.reposition_attempt_count += 1
        logger.info(f"🔄 Reposition deneme: {self.reposition_attempt_count}/{self.cfg.get('reposition_max_attempts')}")
        self._transition(BotState.REPOSITIONING_MOVE)
    def _handle_repositioning_move(self):
        logger.info("🔄 REPOSITION: Move - Klavye hareketi...")
        if self.space_held:
            LowLevelInput.key_up('space')
            self.space_held = False
            logger.info("🔓 Space bırakıldı (hareket için)")
        LowLevelInput.key_up('space')
        try:
            if self.hwnd:
                # Anti-cheat: ctypes veya win32gui rastgele
                if random.choice([True, False]):
                    WinUtils._user32.SetForegroundWindow(self.hwnd)
                else:
                    win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(human_delay(0.1, 0.03))
        except: logger.warning("⚠️ Window focus hatası")
        side_key = random.choice(['a', 'd'])
        LowLevelInput.key_down(side_key); time.sleep(human_delay(0.3, 0.1)); LowLevelInput.key_up(side_key)
        LowLevelInput.key_down('s'); time.sleep(human_delay(0.5, 0.15)); LowLevelInput.key_up('s')
        if self.cfg.get("camera_rotation_enabled"):
            rot_key = random.choice(['q', 'e'])
            LowLevelInput.key_down(rot_key); time.sleep(human_delay(0.2, 0.05)); LowLevelInput.key_up(rot_key)
        time.sleep(human_delay(0.3, 0.1))
        logger.info("✅ Klavye hareketi tamamlandı, hedef aranıyor...")
        self._transition(BotState.REPOSITIONING_FIND)
    def _compare_patches(self, patch1, patch2):
        try:
            if patch1 is None or patch2 is None: return 0.0
            if patch1.shape[0] == 0 or patch1.shape[1] == 0: return 0.0
            if patch2.shape[0] == 0 or patch2.shape[1] == 0: return 0.0
            target_size = (64, 64)
            p1 = cv2.resize(patch1, target_size)
            p2 = cv2.resize(patch2, target_size)
            hsv1 = cv2.cvtColor(p1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(p2, cv2.COLOR_BGR2HSV)
            hist1 = cv2.calcHist([hsv1], [0, 1], None, [30, 32], [0, 180, 0, 256])
            hist2 = cv2.calcHist([hsv2], [0, 1], None, [30, 32], [0, 180, 0, 256])
            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
            score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return max(0.0, score)
        except: return 0.0
    def _handle_repositioning_find(self):
        logger.info("🔄 REPOSITION: Find - Hedef aranıyor...")
        try:
            frame = self.camera.get_latest_frame()
            if frame is None:
                logger.warning("⚠️ Frame alınamadı")
                self._transition(BotState.REPOSITIONING_WAIT)
                return
            rect = WinUtils.get_rect_by_hwnd(self.hwnd)
            if not rect:
                logger.warning("⚠️ Window rect alınamadı")
                self._transition(BotState.REPOSITIONING_WAIT)
                return
            wx, wy, ww, wh = rect
            try:
                self.last_screenshot = frame[wy:wy+wh, wx:wx+ww]
                self.cached_window_rect = rect
            except:
                self._transition(BotState.REPOSITIONING_WAIT)
                return
            
            # Anti-cheat: Saccade Simülasyonu
            self.inference_counter += 1
            if self.inference_counter % random.randint(2, 4) != 0:
                return

            results = self.model.predict(source=self.last_screenshot, conf=self.cfg.get("confidence"), verbose=False, device='cpu')
            candidates = []
            h, w = self.last_screenshot.shape[:2]
            cx, cy = w // 2, h // 2
            if len(results) > 0 and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    tcx, tcy = (x1+x2)//2, (y1+y2)//2
                    dist = ((tcx-cx)**2 + (tcy-cy)**2)**0.5
                    if x1 < 5 or y1 < 5 or x2 > w-5 or y2 > h-5: continue
                    patch = self.last_screenshot[y1:y2, x1:x2]
                    similarity = self._compare_patches(self.target_patch, patch)
                    candidates.append({'cx': tcx, 'cy': tcy, 'bbox': (x1, y1, x2, y2), 'dist': dist, 'similarity': similarity})
            if not candidates:
                logger.warning("⚠️ Hiç metin bulunamadı, beklemeye geçiliyor...")
                self._transition(BotState.REPOSITIONING_WAIT)
                return
            best_target = None
            if self.target_patch is not None:
                candidates.sort(key=lambda c: c['similarity'], reverse=True)
                best_match = candidates[0]
                if best_match['similarity'] > 0.6:
                    best_target = best_match
                    logger.info(f"🎯 Hedef BULUNDU! Benzerlik: {best_match['similarity']:.2f}")
                elif best_match['similarity'] > 0.4:
                    candidates.sort(key=lambda c: c['dist'])
                    best_target = candidates[0]
                    logger.warning(f"⚠️ Orta benzerlik ({best_match['similarity']:.2f}), merkeze en yakın seçildi")
                else:
                    # Çok düşük benzerlik - hedef kaybolmuş, yeni arama yap
                    logger.warning(f"❌ Çok düşük benzerlik ({best_match['similarity']:.2f}), reposition iptal - yeni hedef aranıyor")
                    self.reposition_attempt_count = 0
                    self.reposition_initial_hp = -1
                    self._transition(BotState.SEARCHING)
                    return
            else:
                candidates.sort(key=lambda c: c['dist'])
                best_target = candidates[0]
                logger.info("📍 Hedef patch yok, merkeze en yakın seçildi")
            tx, ty = best_target['cx'], best_target['cy']
            # Anti-cheat Fix #7: Micro delay ve offset
            time.sleep(random.uniform(0.03, 0.1))
            offset_x = int(random.gauss(0, 3))
            offset_y = int(random.gauss(0, 3))
            
            # Teleport yerine human_move kullan
            self.human_move(wx + tx + offset_x, wy + ty + offset_y, duration=0.15)
            
            time.sleep(human_delay(0.05, 0.02))
            LowLevelInput.click()
            logger.info(f"🖱️ Hedefe tıklandı: ({tx},{ty}) Benzerlik: {best_target['similarity']:.2f}")
            x1, y1, x2, y2 = best_target['bbox']
            self.current_target = Target(tx, ty, (x1, y1, x2, y2), 0.9, int(best_target['dist']))
        except Exception as e:
            logger.error(f"Reposition find hatası: {e}")
        self._transition(BotState.REPOSITIONING_WAIT)
    def _handle_repositioning_wait(self):
        elapsed = time.time() - self.last_state_change
        wait_time = float(self.cfg.get("reposition_wait_time"))
        remaining = wait_time - elapsed
        self.update_ui(info=f"⏳ Bekleniyor: {remaining:.1f}s")
        if elapsed >= wait_time:
            logger.info("🔄 REPOSITION: Wait tamamlandı, HP kontrol ediliyor...")
            self._transition(BotState.REPOSITIONING_CHECK)
    def _handle_repositioning_check(self):
        px = self._get_target_bar_pixels()
        if self.reposition_initial_hp > 0:
            hp_diff = self.reposition_initial_hp - px
            threshold = float(self.cfg.get("reposition_hp_threshold"))
            logger.info(f"📊 HP karşılaştırma: {self.reposition_initial_hp}px → {px}px (Fark: {hp_diff}px, Eşik: {threshold}px)")
            if hp_diff > threshold:
                logger.info(f"✅ REPOSITION BAŞARILI! HP azaldı (-{hp_diff}px), saldırıya devam!")
                self.reposition_attempt_count = 0
                self.reposition_initial_hp = -1
                space_mode = self.cfg.get("space_mode")
                if space_mode in ["Daima Basılı Tut", "Hasarda Bas"] and not self.space_held:
                    LowLevelInput.key_down('space')
                    self.space_held = True
                self._transition(BotState.ATTACKING)
                return
            else:
                max_attempts = int(self.cfg.get("reposition_max_attempts"))
                if self.reposition_attempt_count < max_attempts:
                    logger.warning(f"⚠️ HP azalmadı ({hp_diff}px), yeni deneme yapılıyor...")
                    self._transition(BotState.REPOSITIONING_INIT)
                else:
                    logger.warning(f"❌ REPOSITION BAŞARISIZ! {max_attempts} deneme tükendi, yeni hedef aranıyor...")
                    self.reposition_attempt_count = 0
                    self.reposition_initial_hp = -1
                    self._transition(BotState.SEARCHING)
        else:
            logger.warning("⚠️ HP barı okunamadı, yeni hedef aranıyor...")
            self.reposition_attempt_count = 0
            self.reposition_initial_hp = -1
            self._transition(BotState.SEARCHING)

    def _rotate_camera(self, force_direction=None):
        """Anti-cheat Fix #6: Değişken süre ve rastgele yön ile kamera döndürme - LowLevelInput"""
        # Rastgele yön seç (q veya e) veya zorla
        if force_direction:
            direction = force_direction
        else:
            direction = random.choice(['q', 'e'])
            
        LowLevelInput.key_down(direction)
        
        base_dur = float(self.cfg.get("camera_rotation_duration"))
        # Daha geniş varyasyon: %50 - %180
        actual_dur = base_dur * random.uniform(0.5, 1.8)
        time.sleep(human_delay(actual_dur, actual_dur * 0.2))
        
        LowLevelInput.key_up(direction)
        
        # %20 şansla ters yöne de küçük bir dönüş yap (Sadece zorlama yoksa)
        if not force_direction and random.random() < 0.2:
            other_dir = 'e' if direction == 'q' else 'q'
            time.sleep(random.uniform(0.05, 0.15))
            LowLevelInput.key_down(other_dir)
            time.sleep(human_delay(base_dur * 0.3, base_dur * 0.1))
            LowLevelInput.key_up(other_dir)
            
        return actual_dur

    def _handle_captcha(self, popup_rect):
            time.sleep(random.uniform(0.05, 0.15))
            LowLevelInput.key_down(other_dir)
            time.sleep(human_delay(base_dur * 0.3, base_dur * 0.1))
            LowLevelInput.key_up(other_dir)
    def _handle_captcha(self, popup_rect):
        try:
            outliers, confirm = self.captcha_solver.solve(self.last_screenshot, popup_rect)
            if outliers:
                for cx, cy in outliers:
                    rect = WinUtils.get_window_rect(self.pid)
                    if not rect: return
                    LowLevelInput.move_mouse(rect[0]+cx, rect[1]+cy)
                    time.sleep(0.3)
                    LowLevelInput.click()
            if confirm:
                rect = WinUtils.get_window_rect(self.pid)
                if rect:
                    LowLevelInput.move_mouse(rect[0]+confirm[0], rect[1]+confirm[1])
                    time.sleep(0.5)
                    LowLevelInput.click()
                    LowLevelInput.click()
            time.sleep(2)
            self._transition(BotState.SEARCHING)
        except: self._transition(BotState.IDLE)

# ========== GUI ==========
class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

class MetinBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(generate_random_title())
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"750x{screen_h - 80}")
        self.cfg = ConfigManager()
        self.engine = MetinBotEngine(self.cfg, self.update_ui)
        ttk.Style().theme_use('clam')
        
        self.tooltips = {
            "verify_timeout": "Hedefe tıkladıktan sonra HP barının çıkıp çıkmadığını doğrulamak için maksimum bekleme süresi.\nÖrnek: 1.0",
            "hover_delay": "Mouse hedefin üzerine geldikten sonra tıklamadan önce ne kadar bekleyeceği.\nÖrnek: 0.05",
            "double_click": "Hedefe tek tık yerine çift tıklama yapar.",
            "mouse_speed": "Mouse'un hedefe gitme hızı. Düşük değer daha hızlıdır.\nÖrnek: 0.2",
            "use_human_mouse": "Mouse hareketlerini insan gibi kavisli ve değişken hızda yapar (Anti-cheat).",
            "attack_timeout": "Saldırı başladıktan sonra metin kırılmazsa vazgeçme süresi.\nÖrnek: 8.0",
            "damage_verify_timeout": "Saldırı komutundan sonra HP barının gelmesi için beklenecek süre.\nÖrnek: 5.0",
            "hp_stall_timeout": "HP azalmıyorsa takılma var saymak için bekleme süresi.\nÖrnek: 5.0",
            "bar_red_min_pixels": "HP barının var sayılması için gereken minimum kırmızı piksel.\nÖrnek: 25",
            "bar_lost_timeout": "HP barı kaybolduğunda metin kırıldı saymak için bekleme süresi.\nÖrnek: 0.75",
            "hp_jump_threshold": "HP barında ani düşüş (sıçrama) olursa metin kırıldı saymak için eşik.\nÖrnek: 100",
            "zoom_out_enabled": "Otomatik zoom out (F tuşu) özelliğini açar.",
            "zoom_out_on_start": "Bot başladığında bir kez zoom out yapar.",
            "zoom_out_interval": "Belirli aralıklarla zoom out yapar (saniye). 0 ise kapalı.",
            "zoom_out_duration": "F tuşuna basılı tutma süresi.\nÖrnek: 0.8",
            "zoom_out_on_no_target": "Hedef bulunamadığında zoom out yapar.",
            "zoom_out_no_target_interval": "Hedef yoksa ne sıklıkla zoom out yapacağı.\nÖrnek: 5.0",
            "pickup_enabled": "Otomatik eşya toplamayı açar.",
            "pickup_speed": "Toplama tuşuna basma sıklığı (saniye).\nÖrnek: 0.5",
            "space_mode": "Space tuşu davranışı (Kapalı/Daima/Hasarda).",
            "camera_rotation_enabled": "Kamera döndürmeyi açar.",
            "camera_rotation_interval": "Kamera döndürme sıklığı (saniye).\nÖrnek: 1.5",
            "camera_rotation_duration": "Kamera döndürme tuşuna basma süresi.\nÖrnek: 0.2",
            "stuck_detection_enabled": "Takılma algılamayı açar.",
            "stuck_timeout": "Görüntü değişmezse takılma sayma süresi.\nÖrnek: 5.0",
            "stuck_sensitivity": "Takılma algılama hassasiyeti.\nÖrnek: 0.05",
            "pre_search_enabled": "Saldırı sırasında sonraki hedefi aramayı açar.",
            "hp_stall_detection": "HP azalmama durumunu kontrol etmeyi açar.",
            "pre_attack_hp_check": "Saldırmadan önce HP bar kontrolü yapar.",
            "pre_attack_wait_time": "Tıklamadan sonra HP bar kontrolü için bekleme süresi.\nÖrnek: 2.0",
            "skip_no_bar_targets": "HP barı çıkmayan hedefleri atlar.",
            "failed_target_memory_time": "Hatalı hedeflerin hafızada tutulma süresi.\nÖrnek: 60.0",
            "failed_target_radius": "Hatalı hedefin etrafındaki kaçınılacak alan yarıçapı.\nÖrnek: 100"
        }
        
        self.setup_ui()
        self.load_values()
        # keyboard.Listener(on_press=self.on_key).start() # KALDIRILDI
        self.check_keys() # Polling başlat
        
    def check_keys(self):
        """Global hook yerine polling ile tuş kontrolü (Daha güvenli)"""
        if WinUtils.is_key_pressed(0x1B): # VK_ESCAPE
            if self.engine.running:
                self.root.after(0, self.toggle)
                # Tuş bırakılana kadar bekle (debounce)
                while WinUtils.is_key_pressed(0x1B):
                    time.sleep(0.1)
                    self.root.update()
        
        # 100ms sonra tekrar kontrol et
        self.root.after(100, self.check_keys)

    def setup_ui(self):
        pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        left = ttk.Frame(pane, width=350)
        pane.add(left)
        ttk.Label(left, text="Data Analyzer v2.1", font=("Impact", 16)).pack(pady=5)
        ttk.Label(left, text="(Auto Process Detection)", font=("Arial", 8), foreground="gray").pack()
        fm = ttk.LabelFrame(left, text="Main Settings")
        fm.pack(fill="x", padx=5, pady=5)
        
        # YENİ: PID Seçimi (Combobox + Tara Butonu)
        ttk.Label(fm, text="Process:").grid(row=0, column=0, sticky="w", padx=5)
        self.cb_pid = ttk.Combobox(fm, width=25, state="readonly")
        self.cb_pid.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(fm, text="🔄 SCAN", command=self.scan_games, width=8).grid(row=0, column=2, padx=2)
        
        self.add_entry(fm, "Timeout (s):", "attack_timeout", 1)
        self.add_entry(fm, "Confidence:", "conf", 2)
        ttk.Button(fm, text="Data File (.pt)", command=self.sel_model).grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        self.lbl_model = ttk.Label(fm, text="Not loaded", font=("Arial", 8))
        self.lbl_model.grid(row=4, column=0, columnspan=2)
        ff = ttk.LabelFrame(left, text="Features")
        ff.pack(fill="x", padx=5, pady=5)
        self.var_pickup, self.var_stuck, self.var_presearch, self.var_hp_stall, self.var_human_mouse = [tk.BooleanVar() for _ in range(5)]
        self.var_zoom_out, self.var_pre_attack_hp = tk.BooleanVar(), tk.BooleanVar()
        self.var_fast_mode, self.var_aggressive_stuck = tk.BooleanVar(), tk.BooleanVar() # YENİ
        self.var_space_mode = tk.StringVar(value="Hold on Attack")
        
        c1 = ttk.Checkbutton(ff, text="Auto Collect", variable=self.var_pickup)
        c1.grid(row=0, column=0, sticky="w")
        ToolTip(c1, "Automatically collect items from ground.")
        
        ttk.Label(ff, text="Space Modu:").grid(row=1, column=0, sticky="w")
        self.cb_space = ttk.Combobox(ff, textvariable=self.var_space_mode, values=["Kapalı", "Daima Basılı Tut", "Hasarda Bas"], state="readonly", width=12)
        self.cb_space.grid(row=1, column=1, sticky="w", padx=5)
        ToolTip(self.cb_space, "Space tuşu davranışı:\n- Kapalı: Basmaz\n- Daima: Sürekli basılı tutar\n- Hasarda: Sadece hasar vururken basar")
        
        c2 = ttk.Checkbutton(ff, text="Stuck Detect", variable=self.var_stuck)
        c2.grid(row=2, column=0, sticky="w")
        ToolTip(c2, "Botun takıldığını algılar ve kurtulmaya çalışır.")
        
        c3 = ttk.Checkbutton(ff, text="Pre-Search", variable=self.var_presearch)
        c3.grid(row=3, column=0, sticky="w")
        ToolTip(c3, "Saldırı sırasında bir sonraki hedefi arar, böylece zaman kazanır.")
        
        c4 = ttk.Checkbutton(ff, text="HP Stall Detection", variable=self.var_hp_stall)
        c4.grid(row=4, column=0, sticky="w", columnspan=2)
        ToolTip(c4, "Metin kesilirken HP azalmıyorsa (bug/lag) bunu algılar ve işlemi iptal eder.")
        
        c5 = ttk.Checkbutton(ff, text="🔭 Zoom Out (F)", variable=self.var_zoom_out)
        c5.grid(row=5, column=0, sticky="w")
        ToolTip(c5, "Kamerayı uzaklaştırmak için 'F' tuşunu kullanır (Zoom hack varsa).")
        
        c6 = ttk.Checkbutton(ff, text="🛡️ Pre-Attack HP", variable=self.var_pre_attack_hp)
        c6.grid(row=5, column=1, sticky="w")
        ToolTip(c6, "Saldırmadan önce hedefin HP barını kontrol eder, bar yoksa saldırmaz.")
        
        c7 = ttk.Checkbutton(ff, text="⚡ Hızlı Mod", variable=self.var_fast_mode)
        c7.grid(row=6, column=0, sticky="w")
        ToolTip(c7, "Bekleme sürelerini kısaltır ve mouse hızını artırır.")
        
        c8 = ttk.Checkbutton(ff, text="🛑 Agresif Stuck", variable=self.var_aggressive_stuck)
        c8.grid(row=6, column=1, sticky="w")
        ToolTip(c8, "Takılma durumunda daha sert hareketler (180 derece dönüş) yapar.")
        
        ttk.Label(ff, text="Toplama Hız:").grid(row=7, column=0, sticky="w")
        self.ent_pick_spd = ttk.Entry(ff, width=8)
        self.ent_pick_spd.grid(row=7, column=1)
        ttk.Label(ff, text="Bar Eşik (px):").grid(row=8, column=0, sticky="w")
        self.ent_bar_px = ttk.Entry(ff, width=8)
        self.ent_bar_px.grid(row=8, column=1)
        ttk.Label(ff, text="Hasar Timeout (s):").grid(row=9, column=0, sticky="w")
        self.ent_dmg_timeout = ttk.Entry(ff, width=8)
        self.ent_dmg_timeout.grid(row=9, column=1)
        ttk.Label(ff, text="Stuck Timeout (s):").grid(row=10, column=0, sticky="w")
        self.ent_stuck_timeout = ttk.Entry(ff, width=8)
        self.ent_stuck_timeout.grid(row=10, column=1)
        ttk.Label(ff, text="Cam Rot Int (s):").grid(row=11, column=0, sticky="w")
        self.ent_cam_rot_int = ttk.Entry(ff, width=8)
        self.ent_cam_rot_int.grid(row=11, column=1)
        ttk.Label(ff, text="HP Stall (s):").grid(row=12, column=0, sticky="w")
        self.ent_hp_stall = ttk.Entry(ff, width=8)
        self.ent_hp_stall.grid(row=12, column=1)
        ttk.Label(ff, text="Mouse Hız (s):").grid(row=13, column=0, sticky="w")
        self.ent_mouse_spd = ttk.Entry(ff, width=8)
        self.ent_mouse_spd.grid(row=13, column=1)
        ttk.Checkbutton(ff, text="İnsansı Mouse", variable=self.var_human_mouse).grid(row=14, column=0, sticky="w", columnspan=2)
        fbar = ttk.LabelFrame(left, text="Canlı Durum & İstatistik")
        fbar.pack(fill="x", padx=5, pady=5)
        ttk.Button(fbar, text="ALAN SEÇ (HP Bar)", command=self.sel_roi).pack(fill="x")
        # ttk.Button(fbar, text="HP PİKSEL KONTROL", command=self.inspect_hp).pack(fill="x", pady=2) # Kaldırıldı
        
        self.lbl_runtime = tk.Label(fbar, text="Süre: 00:00:00", font=("Arial", 9))
        self.lbl_runtime.pack(anchor="w", padx=5)
        
        self.lbl_stats_10m = tk.Label(fbar, text="Ort. (10dk): 0", font=("Arial", 9))
        self.lbl_stats_10m.pack(anchor="w", padx=5)
        
        self.lbl_stats_1h = tk.Label(fbar, text="Ort. (1sa): 0", font=("Arial", 9))
        self.lbl_stats_1h.pack(anchor="w", padx=5)

        self.lbl_roi = ttk.Label(fbar, text="X", font=("Arial", 8))
        self.lbl_roi.pack()
        fact = ttk.Frame(left)
        fact.pack(fill="x", padx=5, pady=5)
        self.lbl_stat = tk.Label(fact, text="DURUYOR", font=("Arial", 14, "bold"), fg="red")
        self.lbl_stat.pack()
        self.lbl_det = tk.Label(fact, text="...", fg="gray", font=("Arial", 9))
        self.lbl_det.pack()
        self.lbl_cnt = tk.Label(fact, text="Metin: 0", font=("Arial", 11), fg="blue")
        self.lbl_cnt.pack()
        self.btn_run = tk.Button(fact, text="START", bg="green", fg="white", font=("Arial", 11, "bold"), command=self.toggle)
        self.btn_run.pack(fill="x", pady=5)
        ttk.Button(fact, text="Sayacı Sıfırla", command=self.reset_counter).pack(fill="x", pady=2)
        ttk.Button(fact, text="Detaylı Ayarlar", command=self.advanced_settings).pack(fill="x", pady=2)
        ttk.Button(fact, text="KAYDET", command=self.save).pack(fill="x")
        right = ttk.Frame(pane)
        pane.add(right)
        ttk.Label(right, text="📋 CANLI LOGLAR (50 Satır)", font=("Arial", 11, "bold")).pack()
        self.log_text = scrolledtext.ScrolledText(right, width=50, height=40, bg="black", fg="lime", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        logger.addHandler(gui_handler)
        def limit_log(*args):
            lines = self.log_text.get("1.0", tk.END).split('\n')
            if len(lines) > 51:
                self.log_text.delete("1.0", f"{len(lines)-50}.0")
        self.log_text.bind("<<Modified>>", limit_log)
        
        # Başlangıçta otomatik tara
        self.root.after(500, self.scan_games)
        self.add_tooltips()

    def add_tooltips(self):
        # Ana Ayarlar
        ToolTip(self.cb_pid, "Select target process")
        ToolTip(self.ent_attack_timeout, "Maximum attack duration (seconds). Example: 8.0")
        ToolTip(self.ent_conf, "Detection model sensitivity (0.0 - 1.0). Lower value finds more objects but increases false positives. Example: 0.50")
        
        # Özellikler (Entryler)
        ToolTip(self.ent_pick_spd, "Yerdeki eşyaları toplama hızı (saniye).\n'Z' veya '`' tuşuna basma sıklığı.\nÖrnek: 0.5")
        ToolTip(self.ent_bar_px, "Metin taşına saldırıldığını anlamak için HP barında aranan minimum kırmızı piksel sayısı.\nBu değerin altındaysa saldırı başarısız sayılır.\nÖrnek: 25")
        ToolTip(self.ent_dmg_timeout, "Saldırı komutu verildikten sonra HP barının belirmesi için beklenecek süre.\nBu sürede HP barı çıkmazsa saldırı iptal edilir.\nÖrnek: 5.0")
        ToolTip(self.ent_stuck_timeout, "Botun aynı yerde takılı kaldığını anlaması için gereken süre.\nBu süre boyunca görüntü değişmezse takılma giderme modu devreye girer.\nÖrnek: 5.0")
        ToolTip(self.ent_cam_rot_int, "Kameranın ne sıklıkla döndürüleceği (saniye).\nEtraftaki metinleri görmek için kullanılır.\nÖrnek: 1.5")
        ToolTip(self.ent_hp_stall, "HP barı sabit kalırsa (metin kesilmiyorsa) beklenecek süre.\nBu süre sonunda HP düşmezse bot takıldığını varsayar.\nÖrnek: 5.0")
        ToolTip(self.ent_mouse_spd, "Mouse hareket hızı (saniye).\nDaha düşük değer daha hızlı hareket demektir.\nÖrnek: 0.2")

    def add_entry(self, p, t, k, r):
        ttk.Label(p, text=t).grid(row=r, column=0, sticky="w", padx=5)
        e = ttk.Entry(p, width=10)
        e.grid(row=r, column=1, pady=2)
        setattr(self, f"ent_{k}", e)
    
    def scan_games(self):
        """Oyunları tara ve Combobox'a doldur"""
        games = WinUtils.get_metin2_pids()
        if not games:
            self.cb_pid['values'] = ["Game Not Found"]
            self.cb_pid.current(0)
            return
            
        values = [f"{pid} - {title}" for pid, title in games]
        self.cb_pid['values'] = values
        
        # Config'deki son PID'yi bulmaya çalış
        last_pid = self.cfg.get("pid")
        found_index = -1
        for i, (pid, _) in enumerate(games):
            if pid == last_pid:
                found_index = i
                break
        
        if found_index != -1:
            self.cb_pid.current(found_index)
        else:
            self.cb_pid.current(0) # İlkini seç
        
        logger.info(f"🔍 {len(games)} oyun bulundu.")

    def load_values(self):
        c = self.cfg
        # PID artık scan_games ile yükleniyor
        self.ent_attack_timeout.insert(0, c.get("attack_timeout"))
        self.ent_conf.insert(0, c.get("confidence"))
        self.ent_pick_spd.insert(0, c.get("pickup_speed"))
        self.ent_bar_px.insert(0, c.get("bar_red_min_pixels"))
        self.ent_dmg_timeout.insert(0, c.get("damage_verify_timeout"))
        self.ent_stuck_timeout.insert(0, c.get("stuck_timeout"))
        self.ent_cam_rot_int.insert(0, c.get("camera_rotation_interval"))
        self.ent_hp_stall.insert(0, c.get("hp_stall_timeout"))
        self.ent_mouse_spd.insert(0, c.get("mouse_speed"))
        self.var_pickup.set(c.get("pickup_enabled"))
        self.var_human_mouse.set(c.get("use_human_mouse"))
        self.var_space_mode.set(c.get("space_mode"))
        self.var_stuck.set(c.get("stuck_detection_enabled"))
        self.var_presearch.set(c.get("pre_search_enabled"))
        self.var_hp_stall.set(c.get("hp_stall_detection"))
        # YENİ: Zoom Out ve Pre-Attack HP
        self.var_zoom_out.set(c.get("zoom_out_enabled"))
        self.var_pre_attack_hp.set(c.get("pre_attack_hp_check"))
        self.var_fast_mode.set(c.get("fast_mode"))
        self.var_aggressive_stuck.set(c.get("aggressive_stuck"))
        mp = c.get("model_path")
        if mp and os.path.exists(mp): self.engine.load_model(mp)
        r = c.get("target_bar_region")
        if r: self.lbl_roi.config(text=str(r), foreground="green")
    def save(self):
        try:
            c = self.cfg
            # PID'yi Combobox'tan al
            selection = self.cb_pid.get()
            if selection and "Oyun Bulunamadı" not in selection:
                try:
                    pid = int(selection.split(" - ")[0])
                    c.set("pid", pid)
                except: pass
            
            c.set("attack_timeout", float(self.ent_attack_timeout.get()))
            c.set("confidence", float(self.ent_conf.get()))
            c.set("pickup_speed", float(self.ent_pick_spd.get()))
            c.set("bar_red_min_pixels", int(self.ent_bar_px.get()))
            c.set("damage_verify_timeout", float(self.ent_dmg_timeout.get()))
            c.set("stuck_timeout", float(self.ent_stuck_timeout.get()))
            c.set("camera_rotation_interval", float(self.ent_cam_rot_int.get()))
            c.set("hp_stall_timeout", float(self.ent_hp_stall.get()))
            c.set("mouse_speed", float(self.ent_mouse_spd.get()))
            c.set("pickup_enabled", self.var_pickup.get())
            c.set("use_human_mouse", self.var_human_mouse.get())
            c.set("space_mode", self.var_space_mode.get())
            c.set("stuck_detection_enabled", self.var_stuck.get())
            c.set("pre_search_enabled", self.var_presearch.get())
            c.set("hp_stall_detection", self.var_hp_stall.get())
            # YENİ: Zoom Out ve Pre-Attack HP
            c.set("zoom_out_enabled", self.var_zoom_out.get())
            c.set("pre_attack_hp_check", self.var_pre_attack_hp.get())
            c.set("fast_mode", self.var_fast_mode.get())
            c.set("aggressive_stuck", self.var_aggressive_stuck.get())
            c.save()
            messagebox.showinfo("OK", "Saved")
        except:
            messagebox.showerror("Error", "0xE005: Save failed")
    def sel_model(self):
        f = filedialog.askopenfilename(filetypes=[("Network Data", "*.pt"), ("All Files", "*.*")])
        if f: self.engine.load_model(f)
    def sel_roi(self):
        self.root.iconify()
        RegionSelector(self.on_roi)
    def on_roi(self, r):
        self.root.deiconify()
        self.cfg.set("target_bar_region", r)
        self.lbl_roi.config(text=str(r), foreground="green")
        self.save()
    def toggle(self):
        if self.engine.running:
            self.engine.stop()
            self.btn_run.config(text="START", bg="green")
        else:
            # PID Seçimi Kontrolü
            selection = self.cb_pid.get()
            if not selection or "Game Not Found" in selection:
                messagebox.showerror("Error", "0xE006: Select valid process")
                return
            try:
                pid = int(selection.split(" - ")[0])
            except:
                messagebox.showerror("Error", "0xE007: PID parse failed")
                return

            self.save()
            self.engine.set_pid(pid)
            if WinUtils.bring_to_front(pid):
                self.engine.start()
                self.btn_run.config(text="STOP", bg="red")
            else:
                messagebox.showerror("Error", "0xE008: Window focus failed")
    def reset_counter(self):
        if messagebox.askyesno("Reset", "Sayacı sıfırla?"):
            self.engine.reset_counter()
    
    def advanced_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Detaylı Ayarlar - V10.5 Auto")
        win.geometry("750x600")
        win.resizable(False, False)
        canvas = tk.Canvas(win)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        left_params = [
            ("Genel", [("verify_timeout", "Verify Timeout (s)", "float"), ("hover_delay", "Hover Delay (s)", "float"), ("double_click", "Double Click", "bool"), ("mouse_speed", "Mouse Hızı (s)", "float"), ("use_human_mouse", "İnsansı Mouse", "bool")]),
            ("Saldırı", [("attack_timeout", "Attack Timeout (s)", "float"), ("damage_verify_timeout", "Damage Verify (s)", "float"), ("hp_stall_timeout", "HP Stall Timeout (s)", "float")]),
            ("HP Bar", [("bar_red_min_pixels", "Min Pixels", "int"), ("bar_lost_timeout", "Bar Lost Timeout (s)", "float"), ("hp_jump_threshold", "HP Sıçrama Eşiği (px)", "int")]),
            # YENİ: Zoom Out Ayarları
            ("🔭 Zoom Out", [
                ("zoom_out_enabled", "Aktif", "bool"),
                ("zoom_out_on_start", "Başlangıçta", "bool"),
                ("zoom_out_interval", "Periyod (s)", "float"),
                ("zoom_out_duration", "Süre (s)", "float"),
                ("zoom_out_on_no_target", "Hedef Yoksa", "bool"),
                ("zoom_out_no_target_interval", "Hedef Yok Bekleme (s)", "float"),
            ]),
        ]
        right_params = [
            ("Toplama", [("pickup_enabled", "Aktif", "bool"), ("pickup_speed", "Hız (s)", "float"), ("space_mode", "Space Modu", "str")]),
            ("Kamera", [("camera_rotation_enabled", "Aktif", "bool"), ("camera_rotation_interval", "Interval (s)", "float"), ("camera_rotation_duration", "Duration (s)", "float")]),
            ("Stuck Detection", [("stuck_detection_enabled", "Aktif", "bool"), ("stuck_timeout", "Timeout (s)", "float"), ("stuck_sensitivity", "Sensitivity", "float")]),
            ("Diğer", [("pre_search_enabled", "Pre-Search", "bool"), ("hp_stall_detection", "HP Stall Detection", "bool")]),
            # YENİ: Pre-Attack HP Check Ayarları
            ("🛡️ Pre-Attack HP", [
                ("pre_attack_hp_check", "Aktif", "bool"),
                ("pre_attack_wait_time", "Bekleme Süresi (s)", "float"),
                ("skip_no_bar_targets", "Bar Yoksa Atla", "bool"),
                ("failed_target_memory_time", "Hafıza Süresi (s)", "float"),
                ("failed_target_radius", "Hedef Yarıçapı (px)", "int"),
            ]),
        ]
        entries = {}
        left_frame = ttk.Frame(scrollable_frame)
        left_frame.grid(row=0, column=0, padx=10, sticky="n")
        row = 0
        for section, items in left_params:
            ttk.Label(left_frame, text=section, font=("Arial", 11, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 5))
            row += 1
            for key, label, ptype in items:
                desc = self.tooltips.get(key, label)
                ttk.Label(left_frame, text=label + ":").grid(row=row, column=0, sticky="w", padx=5, pady=2)
                if ptype == "bool":
                    var = tk.BooleanVar(value=self.cfg.get(key))
                    chk = ttk.Checkbutton(left_frame, variable=var)
                    chk.grid(row=row, column=1, sticky="w", padx=5)
                    entries[key] = (var, ptype)
                    ToolTip(chk, desc)
                else:
                    entry = ttk.Entry(left_frame, width=12)
                    entry.insert(0, str(self.cfg.get(key)))
                    entry.grid(row=row, column=1, sticky="w", padx=5, pady=2)
                    entries[key] = (entry, ptype)
                    ToolTip(entry, desc)
                row += 1
        right_frame = ttk.Frame(scrollable_frame)
        right_frame.grid(row=0, column=1, padx=10, sticky="n")
        row = 0
        for section, items in right_params:
            ttk.Label(right_frame, text=section, font=("Arial", 11, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 5))
            row += 1
            for key, label, ptype in items:
                desc = self.tooltips.get(key, label)
                ttk.Label(right_frame, text=label + ":").grid(row=row, column=0, sticky="w", padx=5, pady=2)
                if ptype == "bool":
                    var = tk.BooleanVar(value=self.cfg.get(key))
                    chk = ttk.Checkbutton(right_frame, variable=var)
                    chk.grid(row=row, column=1, sticky="w", padx=5)
                    entries[key] = (var, ptype)
                    ToolTip(chk, desc)
                elif ptype == "str":
                    entry = ttk.Entry(right_frame, width=12)
                    entry.insert(0, str(self.cfg.get(key)))
                    entry.grid(row=row, column=1, sticky="w", padx=5, pady=2)
                    entries[key] = (entry, ptype)
                    ToolTip(entry, desc)
                else:
                    entry = ttk.Entry(right_frame, width=12)
                    entry.insert(0, str(self.cfg.get(key)))
                    entry.grid(row=row, column=1, sticky="w", padx=5, pady=2)
                    entries[key] = (entry, ptype)
                    ToolTip(entry, desc)
                row += 1
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill="x", padx=10, pady=10)
        def save_advanced():
            try:
                for key, (widget, ptype) in entries.items():
                    if ptype == "bool": self.cfg.set(key, widget.get())
                    elif ptype == "int": self.cfg.set(key, int(widget.get()))
                    elif ptype == "float": self.cfg.set(key, float(widget.get()))
                    elif ptype == "str": self.cfg.set(key, str(widget.get()))
                self.cfg.save()
                messagebox.showinfo("OK", "Settings saved")
                win.destroy()
            except Exception as e: messagebox.showerror("Error", f"0xE009: {e}")
        ttk.Button(btn_frame, text="KAYDET", command=save_advanced).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="İPTAL", command=win.destroy).pack(side="left", padx=5)
    
    def inspect_hp(self):
        if not self.engine.last_screenshot is not None: return messagebox.showerror("Error", "0xE010: System not running")
        region = self.cfg.get("target_bar_region")
        if not region: return messagebox.showerror("Error", "0xE011: Region not set")
        win = tk.Toplevel(self.root)
        win.title("HP Pixel Inspector")
        win.geometry("500x400")
        info_frame = ttk.Frame(win)
        info_frame.pack(fill="x", padx=10, pady=10)
        lbl_live = tk.Label(info_frame, text="Canlı HP Piksel: ---", font=("Arial", 12, "bold"), fg="blue")
        lbl_live.pack()
        lbl_threshold = tk.Label(info_frame, text=f"Eşik: {self.cfg.get('bar_red_min_pixels')} piksel", font=("Arial", 10))
        lbl_threshold.pack()
        lbl_status = tk.Label(info_frame, text="Durum: ---", font=("Arial", 10))
        lbl_status.pack()
        canvas_frame = ttk.Frame(win)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        lbl_img = tk.Label(canvas_frame, bg="black")
        lbl_img.pack()
        def update():
            try:
                px = self.engine._get_target_bar_pixels()
                lbl_live.config(text=f"Canlı HP Piksel: {px}")
                threshold = int(self.cfg.get('bar_red_min_pixels'))
                if px == 0:
                    status = "❌ BAR YOK (0 piksel)"
                    color = "red"
                elif px < threshold:
                    status = f"⚠️ EŞİĞİN ALTINDA ({px} < {threshold})"
                    color = "orange"
                else:
                    status = f"✅ BAR ALGILANDI ({px} piksel)"
                    color = "green"
                lbl_status.config(text=status, fg=color)
                if self.engine.last_screenshot is not None and self.engine.cached_window_rect:
                    wx, wy, ww, wh = self.engine.cached_window_rect
                    rx, ry, rw, rh = region
                    lx, ly = rx - wx, ry - wy
                    if 0 <= lx < ww and 0 <= ly < wh and rw > 0 and rh > 0:
                        roi = self.engine.last_screenshot[ly:ly+rh, lx:lx+rw]
                        if roi.shape[0] > 0 and roi.shape[1] > 0:
                            try:
                                roi_big = cv2.resize(roi, (rw*4, rh*4), interpolation=cv2.INTER_NEAREST)
                                roi_rgb = cv2.cvtColor(roi_big, cv2.COLOR_BGR2RGB)
                                img = Image.fromarray(roi_rgb)
                                photo = ImageTk.PhotoImage(image=img)
                                lbl_img.config(image=photo)
                                lbl_img.image = photo
                            except: pass
            except Exception as e: lbl_status.config(text=f"Hata: {e}", fg="red")
            if win.winfo_exists(): win.after(200, update)
        update()
        ttk.Button(win, text="KAPAT", command=win.destroy).pack(pady=10)
    def update_ui(self, status=None, color=None, info=None, model_name=None, metin_count=None):
        try:
            if status: self.lbl_stat.config(text=status, fg=color or "black")
            if info: self.lbl_det.config(text=info)
            if model_name: self.lbl_model.config(text=model_name)
            if metin_count is not None: self.lbl_cnt.config(text=f"Metin: {metin_count}")
            
            # İstatistik Güncelleme
            if self.engine.running and self.engine.start_time:
                elapsed = time.time() - self.engine.start_time
                hours, rem = divmod(elapsed, 3600)
                minutes, seconds = divmod(rem, 60)
                self.lbl_runtime.config(text=f"Süre: {int(hours):02}:{int(minutes):02}:{int(seconds):02}")
                
                count = self.engine.metin_count
                if elapsed > 0:
                    # Ortalama hesaplama
                    rate_per_sec = count / elapsed
                    avg_10m = rate_per_sec * 600
                    avg_1h = rate_per_sec * 3600
                    
                    self.lbl_stats_10m.config(text=f"Ort. (10dk): {avg_10m:.1f}")
                    self.lbl_stats_1h.config(text=f"Ort. (1sa): {avg_1h:.1f}")
            else:
                self.lbl_runtime.config(text="Süre: 00:00:00")
                # self.lbl_stats_10m.config(text="Ort. (10dk): 0") # Resetlemeyelim, son durumu göstersin
                # self.lbl_stats_1h.config(text="Ort. (1sa): 0")
                
        except: pass
    # def on_key(self, key): # ARTIK KULLANILMIYOR
    #     if key == keyboard.Key.esc and self.engine.running:
    #         self.root.after(0, self.toggle)

# ========== TEST FONKSİYONU ==========
def test_keyboard():
    """Klavye fonksiyonlarını test et"""
    print("\n" + "="*50)
    print("🔍 KLAVYE TEST BAŞLATIYOR...")
    print("="*50)
    
    if not input_sim:
        print("❌ input_sim başlatılamadı, test iptal edildi!")
        return False
    
    print(f"✅ Input Mode: {input_sim.mode}")
    print("\n⏳ 3 saniye sonra test başlayacak (Notepad/metin düzenleyici açın)...")
    time.sleep(3)
    
    test_keys = [
        ('w', 'W harfi'),
        ('a', 'A harfi'),
        ('s', 'S harfi'),
        ('d', 'D harfi'),
        ('space', 'Space tuşu'),
        ('f', 'F harfi'),
        ('t', 'T harfi')
    ]
    
    print("\n📝 Test ediliyor...")
    success_count = 0
    
    for key, desc in test_keys:
        print(f"\n  Test: {desc} ({key})")
        
        down_result = LowLevelInput.key_down(key)
        time.sleep(0.1)
        up_result = LowLevelInput.key_up(key)
        
        if down_result and up_result:
            print(f"    ✅ Başarılı")
            success_count += 1
        else:
            print(f"    ❌ Başarısız (down={down_result}, up={up_result})")
        
        time.sleep(0.3)
    
    print("\n" + "="*50)
    print(f"📊 Test Sonucu: {success_count}/{len(test_keys)} başarılı")
    print("="*50 + "\n")
    
    return success_count == len(test_keys)

if __name__ == "__main__":
    # Klavye testi yap
    test_keyboard()
    
    # GUI başlat
    root = tk.Tk()
    MetinBotGUI(root)
    root.mainloop()
