"""
SHIVA BOT - Metin Tarayan v1.0
================================
PyQt6 GUI + YOLO + Interception Driver
Anti-Cheat Bypass ile Fiziksel Input Simülasyonu

Tarih: 7 Ocak 2026
"""

import sys
import time
import random
import ctypes
import base64
import math
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSpinBox, QDoubleSpinBox,
    QGroupBox, QMessageBox, QComboBox, QFileDialog, QLineEdit,
    QSystemTrayIcon, QMenu, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont, QTextCursor, QIcon, QAction

# Secure String Manager (XOR Encryption)
from secure_strings import secure_strings
import json
import os

# Enhanced Logger
from logger import EnhancedLogger, LogLevel, LogCategory

# Human Behavior Simulator
from behavior_simulator import HumanBehaviorSimulator, TimingHumanizer, PatternBreaker

# Model Encryption (Anti-Cheat W2 Fix)
from model_encryptor import ModelEncryptor

# Hybrid Capture Manager (Anti-Cheat W3 Fix)
from capture_manager import HybridCaptureManager

# Advanced Anti-Debug (Anti-Cheat W9 Fix)
from anti_debug_advanced import AdvancedAntiDebug

# ==================== CONFIG MANAGER ====================

class ConfigManager:
    """JSON tabanlı ayar yönetimi"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.default_config = {
            "confidence": 0.6,
            "timeout": 12,
            "model_path": "model.pt",
            "last_window_index": 0
        }
    
    def load(self):
        """Config dosyasını yükle"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Default değerlerle merge et (eksik keyler için)
                    return {**self.default_config, **config}
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"Config load error: {e}")
            return self.default_config.copy()
    
    def save(self, config):
        """Config dosyasına kaydet"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Config save error: {e}")
            return False

# ==================== GÜVENLİK KATMANI ====================

def obfuscate_process():
    """Process ismini gizle"""
    try:
        ctypes.windll.kernel32.SetConsoleTitleW("")
    except:
        pass

def check_debugger():
    """
    Gelişmiş debugger tespiti - Sessizce çık
    Multiple detection methods
    """
    try:
        # 1. IsDebuggerPresent
        if ctypes.windll.kernel32.IsDebuggerPresent():
            sys.exit(0)
        
        # 2. CheckRemoteDebuggerPresent
        is_debugged = ctypes.c_bool(False)
        ctypes.windll.kernel32.CheckRemoteDebuggerPresent(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(is_debugged)
        )
        if is_debugged.value:
            sys.exit(0)
        
        # 3. NtGlobalFlag check (PEB)
        # Debugger altında çalışırken PEB.NtGlobalFlag farklı olur
        try:
            import struct
            import platform
            if platform.machine().endswith('64'):
                # 64-bit
                peb_address = ctypes.c_void_p()
                ctypes.windll.ntdll.NtQueryInformationProcess(
                    ctypes.windll.kernel32.GetCurrentProcess(),
                    0,  # ProcessBasicInformation
                    ctypes.byref(peb_address),
                    ctypes.sizeof(peb_address),
                    None
                )
            # Flag kontrolü karmaşık, basit versiyonda skip
        except:
            pass
        
        # 4. Debug port check
        debug_port = ctypes.c_long(0)
        ctypes.windll.ntdll.NtQueryInformationProcess(
            ctypes.windll.kernel32.GetCurrentProcess(),
            7,  # ProcessDebugPort
            ctypes.byref(debug_port),
            ctypes.sizeof(debug_port),
            None
        )
        if debug_port.value != 0:
            sys.exit(0)
            
    except:
        pass

def check_vm():
    """
    Virtual Machine detection
    VM'de çalışıyorsa True döner
    """
    try:
        import winreg
        
        # 1. Registry check - BIOS vendor
        vm_indicators = ['vmware', 'virtualbox', 'qemu', 'xen', 'hyperv', 'parallels']
        
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                r"HARDWARE\DESCRIPTION\System\BIOS")
            bios_vendor = winreg.QueryValueEx(key, "SystemManufacturer")[0].lower()
            winreg.CloseKey(key)
            
            for indicator in vm_indicators:
                if indicator in bios_vendor:
                    return True
        except:
            pass
        
        # 2. Check for VM devices
        vm_files = [
            r"C:\windows\System32\Drivers\Vmmouse.sys",
            r"C:\windows\System32\Drivers\vmhgfs.sys",
            r"C:\windows\System32\Drivers\VBoxMouse.sys",
            r"C:\windows\System32\Drivers\VBoxGuest.sys"
        ]
        
        for vm_file in vm_files:
            if os.path.exists(vm_file):
                return True
        
        return False
    except:
        return False

def check_anticheat():
    """Anti-cheat process tespiti"""
    try:
        import psutil
        suspicious = ['gameguard', 'xigncode', 'easyanticheat', 'battleye', 'vanguard', 'faceit']
        
        for proc in psutil.process_iter(['name']):
            name = proc.info['name'].lower()
            for s in suspicious:
                if s in name:
                    return True
        return False
    except:
        return False

def anti_memory_dump():
    """
    Memory dump protection
    Process memory'yi scan etmeyi zorlaştırır
    """
    try:
        # Process priority'yi düşür (analysis zorlaşır)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(handle, 0x00000040)  # IDLE_PRIORITY_CLASS
        
        # Memory working set'i minimize et
        ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
    except:
        pass

# ==================== WINDOW TOGGLE ====================

class GlobalHotkey:
    """
    INSERT tuşu ile pencereyi göster/gizle
    GetAsyncKeyState ile INSERT tuşunu kontrol eder
    """
    
    def __init__(self, window):
        self.window = window
        self.registered = False
        self.last_insert_state = False
        
        # QTimer ile INSERT tuşu kontrolü
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_insert_key)
    
    def register(self):
        """INSERT tuşu kontrolünü başlat"""
        try:
            # Timer'ı başlat (150ms aralıkla kontrol)
            self.timer.start(150)
            self.registered = True
            return True
        except Exception as e:
            print(f"Hotkey registration failed: {e}")
            return False
    
    def unregister(self):
        """INSERT tuşu kontrolünü durdur"""
        if self.registered:
            try:
                self.timer.stop()
                self.registered = False
            except:
                pass
    
    def check_insert_key(self):
        """INSERT tuşuna basıldı mı kontrol et"""
        try:
            import ctypes
            
            # VK_INSERT = 0x2D (INSERT key)
            VK_INSERT = 0x2D
            
            # GetAsyncKeyState - tuş şu anda basılı mı?
            insert_state = ctypes.windll.user32.GetAsyncKeyState(VK_INSERT) & 0x8000
            
            # INSERT tuşu basıldı (state değişti: false -> true)
            if insert_state and not self.last_insert_state:
                # INSERT'e basıldı - pencereyi toggle et
                self.window.toggle_window()
            
            # Son durumu kaydet
            self.last_insert_state = bool(insert_state)
                    
        except Exception as e:
            pass  # Sessizce devam et

# ==================== WINDOW CAMOUFLAGE ====================

class WindowCamouflage:
    """Pencere başlığını meşru Windows uygulamalarına benzetir"""
    
    LEGIT_TITLES = [
        "Microsoft Edge",
        "Calculator",
        "Discord",
        "Notepad",
        "Windows Security",
        "Task Manager",
        "File Explorer",
        "Settings",
        "Microsoft Store",
        "Paint",
        "Windows Media Player",
        "Snipping Tool",
        "Control Panel",
        "System Properties"
    ]
    
    @staticmethod
    def get_random_title():
        """Rastgele meşru pencere başlığı döndür"""
        return random.choice(WindowCamouflage.LEGIT_TITLES)
    
    @staticmethod
    def get_smart_window_title():
        """
        Get window title that matches actual process name (Anti-Cheat W8 Fix)
        
        When running as python.exe: Random legit title
        When running as EXE: Title matching EXE name
        
        Returns:
            str: Appropriate window title
        """
        import sys
        
        # Get actual executable name
        if getattr(sys, 'frozen', False):
            # Running as compiled EXE
            exe_name = os.path.basename(sys.executable).lower()
        else:
            # Running as Python script
            exe_name = "python.exe"
        
        # Title mapping for common process names
        title_map = {
            # System processes
            'svchost.exe': 'Host Process for Windows Services',
            'explorer.exe': 'File Explorer',
            'dwm.exe': 'Desktop Window Manager',
            'csrss.exe': 'Client Server Runtime Process',
            'winlogon.exe': 'Windows Logon Application',
            'lsass.exe': 'Local Security Authority Process',
            'services.exe': 'Services and Controller App',
            
            # Common applications
            'chrome.exe': 'Google Chrome',
            'msedge.exe': 'Microsoft Edge',
            'firefox.exe': 'Mozilla Firefox',
            'discord.exe': 'Discord',
            'spotify.exe': 'Spotify',
            'steam.exe': 'Steam',
            'notepad.exe': 'Notepad',
            'calc.exe': 'Calculator',
            'taskmgr.exe': 'Task Manager',
            
            # Python (fallback to random)
            'python.exe': random.choice(WindowCamouflage.LEGIT_TITLES),
            'pythonw.exe': random.choice(WindowCamouflage.LEGIT_TITLES)
        }
        
        # Check for svchost variants (svchost_a3f2.exe, etc.)
        if exe_name.startswith('svchost'):
            return 'Host Process for Windows Services'
        
        # Check for exact match
        if exe_name in title_map:
            return title_map[exe_name]
        
        # Fallback: Generic system title
        return 'System Process'

# ==================== MOUSE MOVEMENT UTILS ====================

class BezierMouseMovement:
    """İnsan benzeri Bezier curve mouse hareketi"""
    
    @staticmethod
    def calculate_bezier_points(start_x, start_y, end_x, end_y, steps=20):
        """
        Bezier curve ile smooth mouse path oluştur
        
        Args:
            start_x, start_y: Başlangıç koordinatları
            end_x, end_y: Hedef koordinatlar
            steps: Toplam adım sayısı (daha yüksek = daha smooth)
        
        Returns:
            List of (x, y) tuples
        """
        # Random control points (curve için)
        # İnsan hareketi nadiren düz çizgidir
        distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
        
        # Control point deviation (mesafeye göre)
        deviation = min(distance * 0.3, 50)  # Max 50 piksel sapma
        
        # Control point 1 (başlangıca yakın)
        ctrl1_x = start_x + (end_x - start_x) * 0.33 + random.uniform(-deviation, deviation)
        ctrl1_y = start_y + (end_y - start_y) * 0.33 + random.uniform(-deviation, deviation)
        
        # Control point 2 (hedefe yakın)
        ctrl2_x = start_x + (end_x - start_x) * 0.66 + random.uniform(-deviation, deviation)
        ctrl2_y = start_y + (end_y - start_y) * 0.66 + random.uniform(-deviation, deviation)
        
        points = []
        
        for i in range(steps + 1):
            t = i / steps
            
            # Cubic Bezier formula: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
            x = (
                (1 - t)**3 * start_x +
                3 * (1 - t)**2 * t * ctrl1_x +
                3 * (1 - t) * t**2 * ctrl2_x +
                t**3 * end_x
            )
            
            y = (
                (1 - t)**3 * start_y +
                3 * (1 - t)**2 * t * ctrl1_y +
                3 * (1 - t) * t**2 * ctrl2_y +
                t**3 * end_y
            )
            
            points.append((int(x), int(y)))
        
        return points
    
    @staticmethod
    def randomize_target(cx, cy, radius=5):
        """
        Hedef koordinatı Gaussian distribution ile randomize et
        
        Args:
            cx, cy: Merkez koordinatlar
            radius: Maksimum sapma yarıçapı (piksel)
        
        Returns:
            (x, y) tuple
        """
        # Gaussian distribution (doğal dağılım)
        offset_x = random.gauss(0, radius/2)
        offset_y = random.gauss(0, radius/2)
        
        # Sınırlama (radius içinde kalsın)
        offset_x = max(-radius, min(radius, offset_x))
        offset_y = max(-radius, min(radius, offset_y))
        
        return int(cx + offset_x), int(cy + offset_y)

# ==================== PENCERE YÖNETİMİ ====================

def get_windows_list():
    """Tüm açık pencereleri listele"""
    windows = []
    
    def callback(hwnd, extra):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                title = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, title, length + 1)
                
                # Process ID al
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                
                if title.value:
                    windows.append({
                        'hwnd': hwnd,
                        'title': title.value,
                        'pid': pid.value
                    })
        return True
    
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int)
    )
    
    ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)
    return windows

def get_window_rect(hwnd):
    """Pencere client area koordinatlarını al (title bar/border hariç)"""
    # Client area boyutunu al
    client_rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    
    # Client area sol üst köşesini screen koordinatlarına çevir
    point = ctypes.wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
    
    # Client area için düzeltilmiş koordinatlar
    width = client_rect.right - client_rect.left
    height = client_rect.bottom - client_rect.top
    
    return {
        'left': point.x,
        'top': point.y,
        'right': point.x + width,
        'bottom': point.y + height,
        'width': width,
        'height': height
    }

# Başlangıç güvenlik kontrolleri
obfuscate_process()
check_debugger()

# ==================== BOT THREAD ====================

class BotThread(QThread):
    """Ana bot döngüsü - Ayrı thread'de çalışır"""
    
    log_signal = pyqtSignal(str, str)  # (mesaj, renk)
    stats_signal = pyqtSignal(dict)
    
    def __init__(self, conf_threshold=0.6, timeout=12, target_hwnd=None, model_path='model.pt'):
        super().__init__()
        self.running = False
        self.conf_threshold = conf_threshold
        self.timeout = timeout
        self.target_hwnd = target_hwnd  # Hedef pencere
        self.model_path = model_path  # Model dosya yolu
        
        # Bileşenler
        self.model = None
        self.camera = None
        self.capture_manager = None  # Hybrid Capture Manager - AC-W3
        self.input_device = None
        
        # Pencere koordinatları
        self.window_rect = None
        
        # İstatistikler
        self.target_count = 0
        self.fps = 0
        
        # Human Behavior Simulator
        self.behavior_sim = HumanBehaviorSimulator()
        self.timing = TimingHumanizer()
        self.pattern_breaker = PatternBreaker()
        
        # Advanced Anti-Debug (AC-W9)
        self.anti_debug = AdvancedAntiDebug()
    
    def run(self):
        """Ana bot döngüsü"""
        self.running = True
        
        try:
            # 1. ML Model Yükle (Encrypted Support)
            self.log_signal.emit(secure_strings.get('LOG_MODEL_LOADING', self.model_path), "white")
            
            try:
                from ultralytics import YOLO
                import io
                
                # Check if model is encrypted (.enc extension)
                if self.model_path.endswith('.enc'):
                    self.log_signal.emit("🔒 Encrypted model detected", "yellow")
                    
                    # Delayed loading (5 seconds - anti-memory-scan)
                    self.log_signal.emit("⏳ Delayed loading (5s)...", "white")
                    self.timing.sleep(5.0, variance=0.1)
                    
                    # Decrypt to memory (NO DISK WRITE)
                    encryptor = ModelEncryptor()
                    model_bytes = encryptor.decrypt_model(self.model_path)
                    
                    if model_bytes is None:
                        raise ValueError("Model decryption failed")
                    
                    # Load from memory buffer
                    buffer = io.BytesIO(model_bytes)
                    self.model = YOLO(buffer)
                    
                    # Clear buffer immediately (minimize memory exposure)
                    buffer.close()
                    del model_bytes
                    del encryptor
                    
                    self.log_signal.emit("✅ Encrypted model loaded from memory", "green")
                else:
                    # Standard model loading (not encrypted)
                    self.model = YOLO(self.model_path)
                    self.log_signal.emit(secure_strings.get('LOG_MODEL_READY'), "green")
                    
            except FileNotFoundError:
                self.log_signal.emit(secure_strings.get('LOG_MODEL_NOT_FOUND', self.model_path), "red")
                self.log_signal.emit(secure_strings.get('LOG_MODEL_SELECT'), "yellow")
                return
            except Exception as e:
                self.log_signal.emit(secure_strings.get('LOG_MODEL_ERROR', e), "red")
                return
            
            # 2. Ekran Yakalama Başlat (Hybrid Capture Manager - AC-W3)
            self.log_signal.emit(secure_strings.get('LOG_CAPTURE_START'), "white")
            
            try:
                # Initialize Hybrid Capture Manager
                self.capture_manager = HybridCaptureManager()
                
                # Eğer hedef pencere seçiliyse, sadece o bölgeyi yakala
                self.capture_region = None
                if self.target_hwnd:
                    self.window_rect = get_window_rect(self.target_hwnd)
                    self.log_signal.emit(
                        secure_strings.get('LOG_CAPTURE_REGION', self.window_rect['width'], self.window_rect['height']),
                        "cyan"
                    )
                    
                    # Capture region for hybrid manager
                    self.capture_region = (
                        self.window_rect['left'],
                        self.window_rect['top'],
                        self.window_rect['right'],
                        self.window_rect['bottom']
                    )
                    self.log_signal.emit(f"🎯 Hybrid capture methods: {self.capture_manager.methods}", "cyan")
                else:
                    self.log_signal.emit(f"🎯 Hybrid capture methods: {self.capture_manager.methods}", "cyan")
                
                self.log_signal.emit(secure_strings.get('LOG_CAPTURE_READY'), "green")
            except Exception as e:
                self.log_signal.emit(secure_strings.get('LOG_CAPTURE_ERROR', e), "red")
                return
            
            # 3. Interception Driver Başlat
            self.log_signal.emit(secure_strings.get('LOG_INTERCEPTION_START'), "white")
            
            try:
                import interception
                self.input_device = interception.Interception()
                self.log_signal.emit(secure_strings.get('LOG_INTERCEPTION_READY'), "green")
                self.log_signal.emit(secure_strings.get('LOG_INTERCEPTION_BYPASS'), "cyan")
            except Exception as e:
                self.log_signal.emit("🚨" * 30, "red")
                self.log_signal.emit("❌ KRİTİK HATA: Interception driver yüklenemedi!", "red")
                self.log_signal.emit(f"   ↳ Hata: {e}", "red")
                self.log_signal.emit("━" * 60, "red")
                self.log_signal.emit("⚠️ BOT BAŞLATILMADI - Interception driver zorunludur!", "red")
                self.log_signal.emit("📌 Çözüm Adımları:", "yellow")
                self.log_signal.emit("   1️⃣ install-interception.exe dosyasını çalıştır", "yellow")
                self.log_signal.emit("   2️⃣ 'Install' butonuna tıkla", "yellow")
                self.log_signal.emit("   3️⃣ Bilgisayarı yeniden başlat", "yellow")
                self.log_signal.emit("   4️⃣ Program YÖNETİCİ OLARAK çalıştır", "yellow")
                self.log_signal.emit("━" * 60, "red")
                self.log_signal.emit("🔴 SendInput KULLANILMAYACAK (Anti-Cheat riski %95)", "red")
                self.log_signal.emit("🚨" * 30, "red")
                self.input_device = None
                self.running = False
                return  # Bot çalışmayı durdur
            
            # Input mode özeti (sadece Interception varsa)
            if self.input_device:
                input_mode = secure_strings.get('LOG_INPUT_MODE_INTER')
                self.log_signal.emit(secure_strings.get('LOG_INPUT_MODE', input_mode), "cyan")
            else:
                # Bu noktaya asla gelmemeli çünkü yukarıda return var
                self.log_signal.emit("❌ BOT DURDURULDU", "red")
                return
            self.log_signal.emit(secure_strings.get('LOG_SYSTEM_INITIALIZED'), "cyan")
            self.log_signal.emit(secure_strings.get('LOG_SEPARATOR'), "gray")
            
            # Ana Tarama Döngüsü
            loop_start = time.time()
            frame_count = 0
            
            while self.running:
                frame_start = time.time()
                
                # Anti-Debug check (AC-W9: Random 10% chance)
                if not self.anti_debug.check_and_handle():
                    return  # Debugger detected, exit silently
                
                # Ekran yakala (Hybrid - AC-W3)
                frame = self.capture_manager.capture_smart(self.capture_region)
                if frame is None:
                    # Timing control handled by capture_manager
                    time.sleep(0.05)  # Brief sleep
                    continue
                
                # YOLO ile tara
                results = self.model(frame, conf=self.conf_threshold, verbose=False)
                
                # FPS hesapla
                frame_count += 1
                if frame_count % 30 == 0:  # Her 30 frame'de bir güncelle
                    elapsed = time.time() - loop_start
                    self.fps = int(frame_count / elapsed)
                    self.stats_signal.emit({
                        'targets': self.target_count,
                        'fps': self.fps
                    })
                
                # Hedef var mı?
                if len(results[0].boxes) > 0:
                    box = results[0].boxes[0]
                    confidence = float(box.conf[0])
                    
                    # Merkez koordinat hesapla
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    
                    # Eğer pencere seçiliyse, koordinatları pencere offset'i ile ayarla
                    if self.window_rect:
                        cx += self.window_rect['left']
                        cy += self.window_rect['top']
                    
                    # Random offset (pattern bypass)
                    cx += random.randint(-3, 3)
                    cy += random.randint(-3, 3)
                    
                    self.target_count += 1
                    self.log_signal.emit(
                        secure_strings.get('LOG_OBJECT_DETECTED', self.target_count, cx, cy, confidence),
                        "yellow"
                    )
                    
                    # Aksiyon başlat
                    self.attack_target(cx, cy)
                    
                    # İstatistik güncelle
                    self.stats_signal.emit({
                        'targets': self.target_count,
                        'fps': self.fps
                    })
                
                # Tarama aralığı (human-like)
                base_scan_delay = 0.35
                scan_delay = self.behavior_sim.get_action_delay(base_scan_delay)
                self.timing.sleep(scan_delay, variance=0.2)
            
        except Exception as e:
            self.log_signal.emit(secure_strings.get('LOG_CRITICAL_ERROR', e), "red")
        
        self.log_signal.emit(secure_strings.get('LOG_SEPARATOR'), "gray")
        self.log_signal.emit(secure_strings.get('LOG_SYSTEM_STOPPED'), "red")
    
    def attack_target(self, x, y):
        """Hedefe saldırı yap"""
        try:
            # 1. Click Preparation
            self.log_signal.emit(secure_strings.get('LOG_TARGETING'), "cyan")
            
            # Pre-click delay (human-like)
            pre_click_delay = self.behavior_sim.get_action_delay(0.5)
            self.timing.sleep(pre_click_delay, variance=0.2)
            
            # Human behavior: Hata yapma kontrolü (AC-W6: Context-aware + correction trajectory)
            if self.behavior_sim.should_make_mistake():
                # Get screen center for bias calculation
                screen_center_x = 960  # Assume 1920x1080, adjust if needed
                
                # Get biased mistake with target awareness
                mistake_offset = self.behavior_sim.get_mistake_offset(x, y, screen_center_x)
                x_mistake = x + mistake_offset[0]
                y_mistake = y + mistake_offset[1]
                
                # Move to mistake position
                self._interception_smooth_move(x_mistake, y_mistake)
                self.log_signal.emit(f"🎯 Yanlış hedef (human mistake): {mistake_offset}", "gray")
                self.behavior_sim.increment_mistake()
                
                # Correction trajectory (multi-step, non-instant)
                trajectory = self.behavior_sim.get_correction_trajectory(mistake_offset)
                for offset in trajectory:
                    x_correct = x_mistake - offset[0]
                    y_correct = y_mistake - offset[1]
                    self._interception_smooth_move(x_correct, y_correct)
                    self.timing.sleep(0.05, variance=0.3)  # Quick corrections
                
                # Final precise move to target
                x = x
                y = y
            
            # Hedef koordinatı randomize et (Gaussian distribution)
            # Human behavior: Variance artar (yorgunluk ile)
            variance_multiplier = self.behavior_sim.get_mouse_movement_variance()
            base_radius = 5 * variance_multiplier
            final_x, final_y = BezierMouseMovement.randomize_target(x, y, radius=int(base_radius))
            
            # Mouse hareketi + tıklama (Sadece Interception)
            if not self.input_device:
                self.log_signal.emit("❌ HATA: Interception yok, bot durdu!", "red")
                self.running = False
                return
            
            # Interception ile fiziksel input (Bezier curve)
            self._interception_smooth_move_and_click(final_x, final_y)
            self.log_signal.emit(secure_strings.get('LOG_CLICK_SUCCESS'), "green")
            
            # 2. Action Loop
            input_mode_icon = "🔑"
            input_mode_text = "Interception"
            self.log_signal.emit(secure_strings.get('LOG_PROCESSING', input_mode_icon, input_mode_text), "cyan")
            
            timeout = random.uniform(self.timeout - 2, self.timeout + 2)
            start_time = time.time()
            attack_count = 0
            
            while time.time() - start_time < timeout and self.running:
                # E tuşu bas (sağa dön)
                attack_count += 1
                
                # Interception kontrolü (güvenlik için)
                if not self.input_device:
                    self.log_signal.emit("❌ Interception kaybedildi!", "red")
                    self.running = False
                    break
                
                # Human behavior: Mikro pause kontrolü
                if self.behavior_sim.should_take_micro_pause():
                    pause_duration = self.behavior_sim.get_micro_pause_duration()
                    self.log_signal.emit(f"⏸️ Mikro pause: {pause_duration:.1f}s", "gray")
                    self.timing.sleep(pause_duration)
                    self.behavior_sim.increment_pause()
                
                # Human behavior: Rest break kontrolü (AC-W5: Variable breaks)
                should_break, duration = self.behavior_sim.should_take_rest_break()
                if should_break:
                    self.log_signal.emit(f"☕ Mola zamanı: {duration/60:.1f} dakika", "yellow")
                    self.timing.sleep(duration)
                    self.behavior_sim.increment_pause()
                
                # Interception ile human-like key press
                self._interception_key_press('e')
                self.behavior_sim.increment_action()
                
                # Post-action delay (human-like)
                base_delay = 0.18  # Temel gecikme
                human_delay = self.behavior_sim.get_action_delay(base_delay)
                self.timing.sleep(human_delay, variance=0.15)
                
                # Her 3-5 aksiyonda bir hedef kontrolü
                if attack_count % 4 == 0:
                    frame = self.camera.grab()
                    if frame is not None:
                        results = self.model(frame, conf=self.conf_threshold, verbose=False)
                        
                        if len(results[0].boxes) == 0:
                            elapsed = time.time() - start_time
                            self.log_signal.emit(
                                secure_strings.get('LOG_OBJECT_ELIMINATED', elapsed),
                                "green"
                            )
                            # Başarı sonrası bekle (human-like)
                            self.timing.sleep_range(0.5, 1.0)
                            return
            
            # Timeout
            self.log_signal.emit(
                secure_strings.get('LOG_TIMEOUT', self.timeout),
                "yellow"
            )
            self.timing.sleep_range(0.5, 1.0)
            
        except Exception as e:
            self.log_signal.emit(secure_strings.get('LOG_ACTION_ERROR', e), "red")
    
    def _interception_smooth_move_and_click(self, target_x, target_y):
        """
        Interception ile smooth Bezier curve movement + click
        
        Args:
            target_x, target_y: Hedef koordinatlar
        """
        try:
            import interception
            
            # Mevcut mouse pozisyonunu al (Windows API)
            point = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            start_x, start_y = point.x, point.y
            
            # Bezier curve path hesapla
            # Mesafeye göre step sayısı ayarla (uzun mesafe = daha fazla step)
            distance = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
            steps = max(10, min(30, int(distance / 20)))  # 10-30 arası
            
            path = BezierMouseMovement.calculate_bezier_points(
                start_x, start_y, target_x, target_y, steps=steps
            )
            
            # Bezier curve boyunca hareket et
            for i, (px, py) in enumerate(path):
                # Interception helper: move_relative
                if i == 0:
                    continue  # İlk nokta mevcut pozisyon
                
                prev_x, prev_y = path[i-1]
                dx = px - prev_x
                dy = py - prev_y
                
                # Helper fonksiyon kullan (çok daha basit!)
                interception.move_relative(dx, dy)
                
                # Human-like speed variation
                # Hareket başlangıcında ve sonunda yavaş, ortada hızlı
                progress = i / steps
                if progress < 0.3 or progress > 0.7:
                    delay = random.uniform(0.01, 0.02)  # Yavaş
                else:
                    delay = random.uniform(0.005, 0.01)  # Hızlı
                
                time.sleep(delay)
            
            # Varışta mikro-pause (insan her zaman yapar)
            time.sleep(random.uniform(0.05, 0.15))
            
            # Click işlemi (helper fonksiyon)
            interception.click()
            
        except Exception as e:
            self.log_signal.emit(secure_strings.get('LOG_INTERCEPTION_MOUSE_ERROR', e), "red")
            self.log_signal.emit("❌ Mouse hareketi başarısız, bot durduruluyor...", "red")
            self.running = False
    
    def _interception_key_press(self, key):
        """
        Interception ile human-like keyboard input
        
        Args:
            key: Basılacak tuş (string: 'e', 'w', 'space' vb)
        """
        try:
            from interception import key_down, key_up, Keys
            
            # Key mapping
            key_map = {
                'e': Keys.E,
                'w': Keys.W,
                'a': Keys.A,
                's': Keys.S,
                'd': Keys.D,
                'space': Keys.SPACE,
                'shift': Keys.SHIFT,
                'ctrl': Keys.CONTROL,
            }
            
            scan_code = key_map.get(key.lower(), Keys.E)
            
            # Key down timing (insan her basışta farklı hızda basar)
            press_duration = random.uniform(0.08, 0.15)
            
            # Nadir double tap (insan bazen yanlışlıkla iki kere basar)
            # %3 şans
            will_double_tap = random.random() < 0.03
            
            # İlk basış
            key_down(scan_code)
            time.sleep(press_duration)
            key_up(scan_code)
            
            # Double tap
            if will_double_tap:
                # Çok kısa delay
                time.sleep(random.uniform(0.02, 0.05))
                key_down(scan_code)
                time.sleep(random.uniform(0.06, 0.12))
                key_up(scan_code)
            
        except Exception as e:
            self.log_signal.emit(secure_strings.get('LOG_INTERCEPTION_KEYBOARD_ERROR', e), "red")
            self.log_signal.emit("❌ Keyboard input başarısız, bot durduruluyor...", "red")
            self.running = False
    
    # SendInput fallback fonksiyonları KALDIRILDİ
    # Sebep: Anti-cheat tespit riski %95 (user-mode API)
    # Çözüm: Interception driver zorunlu (kernel-level)
    # Eğer Interception yüklenemezse bot çalışmayacak
    
    def stop(self):
        """Thread'i durdur"""
        self.running = False

# ==================== ANA PENCERE ====================

class MainWindow(QMainWindow):
    """Ana GUI penceresi"""
    
    def __init__(self):
        super().__init__()
        
        # Enhanced Logger başlat
        self.logger = EnhancedLogger(log_dir="logs", auto_save=True)
        self.logger.log_signal.connect(self.add_log_from_logger)
        
        # Config Manager başlat
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        
        # Anti-cheat kontrolü
        if check_anticheat():
            QMessageBox.warning(
                self,
                "⚠️ Güvenlik Uyarısı",
                "Şüpheli program tespit edildi!\nBot çalışmayabilir."
            )
        
        self.bot_thread = None
        self.init_ui()
        self.apply_dark_theme()
        self.setup_tray_icon()
        
        # Config'i yükle (UI bileşenleri oluşturulduktan sonra)
        self.load_config_to_ui()
        
        # Global hotkey'i setup_tray_icon'dan sonra yükle
        self.setup_global_hotkey()
        
        # İlk log
        self.logger.info(LogCategory.SYS, "System initialized ✅")
    
    def init_ui(self):
        """GUI bileşenlerini oluştur"""
        # Pencere başlığını kamufle et (Smart Title Matching - AC-W8)
        self.setWindowTitle(WindowCamouflage.get_smart_window_title())
        self.setGeometry(100, 100, 1000, 450)  # Yükseklik kısaltıldı
        self.setFixedSize(1000, 450)  # Boyut sabitle
        
        # Alt+Tab'dan gizlemek için window flags ayarla
        try:
            from PyQt6.QtCore import Qt
            # WS_EX_TOOLWINDOW flag ile Alt+Tab'da görünmez yap
            self.setWindowFlag(Qt.WindowType.Tool, True)
        except Exception as e:
            pass  # Hata olursa sessizce devam et
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # İKİ KOLONLU DÜZEN (Ana Layout)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # ========== SOL KOLON: KONTROLLER ==========
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        # ========== SOL KOLON: KONTROLLER ==========
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        # ========== MODEL SEÇİMİ ==========
        model_group = QGroupBox(secure_strings.get('MODEL_GROUP'))
        model_layout = QHBoxLayout()
        model_layout.setSpacing(5)
        
        model_label = QLabel(secure_strings.get('MODEL_LABEL'))
        model_label.setMinimumWidth(50)
        model_layout.addWidget(model_label)
        
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setText("model.pt")
        self.model_path_edit.setReadOnly(True)
        self.model_path_edit.setMinimumHeight(28)
        model_layout.addWidget(self.model_path_edit, 1)
        
        model_browse_btn = QPushButton("📁")
        model_browse_btn.clicked.connect(self.browse_model)
        model_browse_btn.setMaximumWidth(40)
        model_browse_btn.setMinimumHeight(28)
        model_browse_btn.setToolTip(secure_strings.get('MODEL_BROWSE_TOOLTIP'))
        model_layout.addWidget(model_browse_btn)
        
        model_group.setLayout(model_layout)
        left_column.addWidget(model_group)
        
        # ========== PENCERE SEÇİMİ ==========
        window_group = QGroupBox(secure_strings.get('WINDOW_GROUP'))
        window_layout = QHBoxLayout()
        window_layout.setSpacing(5)
        
        window_label = QLabel(secure_strings.get('WINDOW_LABEL'))
        window_label.setMinimumWidth(50)
        window_layout.addWidget(window_label)
        
        self.window_combo = QComboBox()
        self.window_combo.setMinimumHeight(28)
        self.refresh_windows()
        window_layout.addWidget(self.window_combo, 1)
        
        refresh_btn = QPushButton(secure_strings.get('WINDOW_REFRESH'))
        refresh_btn.clicked.connect(self.refresh_windows)
        refresh_btn.setMaximumWidth(40)
        refresh_btn.setMinimumHeight(28)
        refresh_btn.setToolTip(secure_strings.get('WINDOW_REFRESH_TOOLTIP'))
        window_layout.addWidget(refresh_btn)
        
        window_group.setLayout(window_layout)
        left_column.addWidget(window_group)
        
        # ========== AYARLAR (KOMPAKT) ==========
        settings_group = QGroupBox(secure_strings.get('SETTINGS_GROUP'))
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(10)
        
        # Confidence
        conf_label = QLabel(secure_strings.get('CONF_LABEL'))
        conf_label.setMinimumWidth(50)
        settings_layout.addWidget(conf_label)
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 1.0)
        self.conf_spin.setValue(0.6)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setDecimals(2)
        self.conf_spin.setMaximumWidth(70)
        self.conf_spin.setMinimumHeight(28)
        self.conf_spin.valueChanged.connect(self.on_config_changed)
        settings_layout.addWidget(self.conf_spin)
        
        settings_layout.addWidget(QLabel("  "))
        
        timeout_label = QLabel(secure_strings.get('TIMEOUT_LABEL'))
        settings_layout.addWidget(timeout_label)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 30)
        self.timeout_spin.setValue(12)
        self.timeout_spin.setSuffix("s")
        self.timeout_spin.setMaximumWidth(70)
        self.timeout_spin.setMinimumHeight(28)
        self.timeout_spin.valueChanged.connect(self.on_config_changed)
        settings_layout.addWidget(self.timeout_spin)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        left_column.addWidget(settings_group)
        
        # ========== DURUM (KOMPAKT) ==========
        status_group = QGroupBox(secure_strings.get('STATS_GROUP'))
        status_layout = QHBoxLayout()
        status_layout.setSpacing(15)
        
        self.status_label = QLabel("⭕ DURDUK")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #ff9800;")
        status_layout.addWidget(self.status_label)
        
        self.hedef_label = QLabel("🎯 0")
        self.hedef_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(self.hedef_label)
        
        self.fps_label = QLabel("📈 0 FPS")
        self.fps_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(self.fps_label)
        
        status_layout.addStretch()
        status_group.setLayout(status_layout)
        left_column.addWidget(status_group)
        
        # ========== KONTROL BUTONLARI (KOMPAKT) ==========
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.start_btn = QPushButton(secure_strings.get('BTN_START'))
        self.start_btn.clicked.connect(self.start_bot)
        self.start_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        self.stop_btn = QPushButton(secure_strings.get('BTN_STOP'))
        self.stop_btn.clicked.connect(self.stop_bot)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        left_column.addLayout(button_layout)
        
        # Sol kolon bitti - alttaki butonları en alta yapıştır (QSpacerItem)
        from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        left_column.addItem(spacer)
        
        # Sol kolonu main layout'a ekle (400px genişlik)
        left_widget = QWidget()
        left_widget.setLayout(left_column)
        left_widget.setFixedWidth(400)
        main_layout.addWidget(left_widget)
        
        # ========== SAĞ KOLON: LOG EKRANI (FULL HEIGHT) ==========
        right_column = QVBoxLayout()
        right_column.setSpacing(5)
        
        # LOG TOOLBAR (Üstte)
        log_toolbar = QHBoxLayout()
        log_toolbar.setSpacing(10)
        
        # Log Level Filter
        log_level_label = QLabel("📊 Level:")
        log_toolbar.addWidget(log_level_label)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        self.log_level_combo.currentTextChanged.connect(self.on_log_level_changed)
        self.log_level_combo.setMinimumHeight(28)
        self.log_level_combo.setMaximumWidth(120)
        log_toolbar.addWidget(self.log_level_combo)
        
        log_toolbar.addWidget(QLabel("  "))
        
        # Auto-save checkbox
        self.auto_save_checkbox = QCheckBox("💾 Auto-save")
        self.auto_save_checkbox.setChecked(True)
        self.auto_save_checkbox.stateChanged.connect(self.on_auto_save_changed)
        log_toolbar.addWidget(self.auto_save_checkbox)
        
        log_toolbar.addStretch()
        
        # Save Log button
        save_log_btn = QPushButton("💾 Save")
        save_log_btn.clicked.connect(self.save_log_manual)
        save_log_btn.setMaximumWidth(80)
        save_log_btn.setMinimumHeight(28)
        save_log_btn.setToolTip("Mevcut log'u dosyaya kaydet")
        log_toolbar.addWidget(save_log_btn)
        
        # Clear Log button
        clear_log_btn = QPushButton("🗑️ Clear")
        clear_log_btn.clicked.connect(self.clear_log)
        clear_log_btn.setMaximumWidth(80)
        clear_log_btn.setMinimumHeight(28)
        clear_log_btn.setToolTip("Log ekranını temizle")
        log_toolbar.addWidget(clear_log_btn)
        
        right_column.addLayout(log_toolbar)
        
        log_group = QGroupBox(secure_strings.get('LOG_GROUP'))
        log_layout = QVBoxLayout()
        log_layout.setSpacing(5)
        log_layout.setContentsMargins(5, 5, 5, 5)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 12))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # MaxHeight kaldırıldı - full height
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        right_column.addWidget(log_group)
        
        # Sağ kolonu main layout'a ekle
        main_layout.addLayout(right_column, 1)  # stretch=1
        
        # Başlangıç log mesajları
        self.show_startup_logs()
    
    def show_startup_logs(self):
        """İlk açılışta sistem bilgileri ve uyarılar"""
        import platform
        import sys
        
        # Başlık
        self.add_log(secure_strings.get('BANNER_TOP'), "cyan")
        self.add_log(secure_strings.get('BANNER_TITLE'), "cyan")
        self.add_log(secure_strings.get('BANNER_SUBTITLE'), "cyan")
        self.add_log(secure_strings.get('BANNER_BOTTOM'), "cyan")
        self.add_log("", "white")
        
        # Sistem bilgileri
        self.add_log(secure_strings.get('SYS_INFO_TITLE'), "white")
        self.add_log(secure_strings.get('SYS_INFO_OS', platform.system(), platform.release()), "gray")
        self.add_log(secure_strings.get('SYS_INFO_PYTHON', sys.version.split()[0]), "gray")
        self.add_log(secure_strings.get('SYS_INFO_PYQT', QApplication.instance().applicationVersion() or '6.x'), "gray")
        self.add_log("", "white")
        
        # Interception driver kontrolü
        self.add_log(secure_strings.get('INTERCEPTION_CHECK'), "white")
        try:
            import interception
            # Test context oluştur
            test_ctx = interception.Interception()
            self.add_log(secure_strings.get('INTERCEPTION_OK_1'), "green")
            self.add_log(secure_strings.get('INTERCEPTION_OK_2'), "green")
            self.add_log(secure_strings.get('INTERCEPTION_OK_3'), "cyan")
            del test_ctx
        except ImportError:
            self.add_log(secure_strings.get('INTERCEPTION_FAIL_1'), "red")
            self.add_log(secure_strings.get('INTERCEPTION_FAIL_2'), "yellow")
        except Exception as e:
            self.add_log(secure_strings.get('INTERCEPTION_FAIL_3'), "yellow")
            self.add_log(secure_strings.get('INTERCEPTION_FAIL_4', str(e)[:50]), "yellow")
            self.add_log(secure_strings.get('INTERCEPTION_FAIL_5'), "red")
        
        self.add_log("", "white")
        
        # Güvenlik uyarıları
        self.add_log(secure_strings.get('SEC_WARNING_TITLE'), "yellow")
        self.add_log(secure_strings.get('SEC_WARNING_1'), "yellow")
        self.add_log(secure_strings.get('SEC_WARNING_2'), "yellow")
        self.add_log(secure_strings.get('SEC_WARNING_3'), "yellow")
        self.add_log("", "white")
        
        self.add_log(secure_strings.get('READY_SEPARATOR'), "gray")
        self.add_log(secure_strings.get('READY_MESSAGE'), "green")
    
    def apply_dark_theme(self):
        """Dark tema uygula"""
        dark_stylesheet = """
        QMainWindow {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            font-size: 12px;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 4px;
            margin-top: 10px;
            font-weight: bold;
            padding-top: 10px;
            font-size: 11px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 3px;
        }
        QLabel {
            color: #ffffff;
            font-size: 11px;
        }
        QTextEdit {
            background-color: #0d1117;
            color: #00ff00;
            border: 1px solid #30363d;
            border-radius: 4px;
            padding: 5px;
            font-size: 10px;
        }
        QSpinBox, QDoubleSpinBox {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 5px;
            font-size: 11px;
        }
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            background-color: #3a3a3a;
            width: 16px;
        }
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            background-color: #3a3a3a;
            width: 16px;
        }
        QComboBox {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 5px;
            font-size: 11px;
        }
        QLineEdit {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 5px;
            font-size: 11px;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid #ffffff;
        }
        QPushButton {
            font-size: 11px;
        }
        """
        self.setStyleSheet(dark_stylesheet)
    
    def setup_tray_icon(self):
        """System tray icon kurulumu"""
        # Tray icon oluştur (Windows default icon)
        self.tray_icon = QSystemTrayIcon(self)
        
        # Icon ayarla - QApplication'ın default icon'u veya basit bir style icon
        try:
            # Windows default application icon
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        except:
            # Fallback: QApplication icon
            self.tray_icon.setIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ComputerIcon))
        
        # Tooltip
        self.tray_icon.setToolTip("System Monitor v2.1")
        
        # Tray menü oluştur
        tray_menu = QMenu()
        
        # Show/Hide action
        show_action = QAction("Show/Hide", self)
        show_action.triggered.connect(self.toggle_window)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # Start action
        self.tray_start_action = QAction("▶ Start", self)
        self.tray_start_action.triggered.connect(self.start_bot)
        tray_menu.addAction(self.tray_start_action)
        
        # Stop action
        self.tray_stop_action = QAction("⏸ Stop", self)
        self.tray_stop_action.triggered.connect(self.stop_bot)
        self.tray_stop_action.setEnabled(False)
        tray_menu.addAction(self.tray_stop_action)
        
        tray_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)
        
        # Menüyü tray icon'a bağla
        self.tray_icon.setContextMenu(tray_menu)
        
        # Double-click ile toggle
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Tray icon'u göster
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        """Tray icon tıklandığında"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()
    
    def toggle_window(self):
        """Pencereyi göster/gizle"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
    
    def quit_application(self):
        """Uygulamayı tamamen kapat"""
        # Bot çalışıyorsa durdur
        if self.bot_thread and self.bot_thread.running:
            self.stop_bot()
            # Thread'in durmasını bekle
            self.bot_thread.wait(1000)
        
        # Global hotkey fonksiyonu kaldırıldı
        
        # Tray icon'u kaldır
        self.tray_icon.hide()
        
        # Uygulamayı kapat
        QApplication.quit()
    
    def closeEvent(self, event):
        """Pencere kapatılırken - tray'e minimize et ve config kaydet"""
        # Config'i kaydet
        self.save_config()
        
        event.ignore()  # Kapatmayı engelle
        self.hide()  # Sadece gizle
        
        # İlk seferde bilgilendirme
        if not hasattr(self, '_tray_notified'):
            self.tray_icon.showMessage(
                "System Monitor",
                "Application minimized to tray.\nDouble-click tray icon to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            self._tray_notified = True
    
    def setup_global_hotkey(self):
        """Global hotkey kurulumu (INSERT tuşu)"""
        try:
            self.hotkey = GlobalHotkey(self)
            
            if self.hotkey.register():
                # Başarıyla kaydedildi - log'a yaz
                self.logger.info(LogCategory.SYS, "⌨️ Global Hotkey: INSERT key registered ✅")
                self.logger.info(LogCategory.SYS, "   ↳ 🔑 INSERT tuşu ile pencereyi göster/gizle")
            else:
                # Kayıt başarısız - log'a yaz
                self.logger.warning(LogCategory.SYS, "⚠️ Global Hotkey registration failed")
        except Exception as e:
            # Hata oluştu
            self.logger.error(LogCategory.SYS, f"❌ Global Hotkey error: {e}")
    
    def load_config_to_ui(self):
        """Config dosyasından ayarları UI'a yükle"""
        try:
            # Spinbox değerlerini ayarla
            self.conf_spin.setValue(self.config.get('confidence', 0.6))
            self.timeout_spin.setValue(self.config.get('timeout', 12))
            
            # Model path ayarla
            model_path = self.config.get('model_path', 'model.pt')
            self.model_path_edit.setText(model_path)
            
            # Window index ayarla (window_combo dolu olmalı)
            window_index = self.config.get('last_window_index', 0)
            if window_index < self.window_combo.count():
                self.window_combo.setCurrentIndex(window_index)
            
            self.logger.info(LogCategory.SYS, "💾 Config yüklendi")
        except Exception as e:
            self.logger.warning(LogCategory.SYS, f"⚠️ Config yükleme hatası: {e}")
    
    def save_config(self):
        """UI ayarlarını config dosyasına kaydet"""
        try:
            self.config = {
                'confidence': self.conf_spin.value(),
                'timeout': self.timeout_spin.value(),
                'model_path': self.model_path_edit.text(),
                'last_window_index': self.window_combo.currentIndex()
            }
            
            if self.config_manager.save(self.config):
                self.logger.info(LogCategory.SYS, "💾 Ayarlar kaydedildi")
                return True
            else:
                self.logger.warning(LogCategory.SYS, "⚠️ Config kaydetme hatası")
                return False
        except Exception as e:
            self.logger.error(LogCategory.SYS, f"❌ Config kaydetme hatası: {e}")
            return False
    
    def on_config_changed(self):
        """Config değiştiğinde otomatik kaydet"""
        # UI bileşenlerinden sonra çağrılır
        if hasattr(self, 'config_manager'):
            self.save_config()
    
    def browse_model(self):
        """Model dosyası seç"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "YOLO Model Seç",
            "",
            "YOLO Model (*.pt *.pth);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            self.model_path_edit.setText(file_path)
            self.logger.info(LogCategory.MDL, f"🎯 Model seçildi: {file_path}")
            # Config'i kaydet
            self.save_config()
    
    def refresh_windows(self):
        """Pencere listesini yenile"""
        self.window_combo.clear()
        self.window_combo.addItem(secure_strings.get('WINDOW_ALL_SCREEN'), None)
        
        windows = get_windows_list()
        for win in windows:
            # Boş başlıkları ve kendi penceremizi atla
            if win['title'] and "SHIVA" not in win['title']:
                display_text = f"{win['title'][:40]} (PID: {win['pid']})"
                self.window_combo.addItem(display_text, win['hwnd'])
    
    def start_bot(self):
        """Bot'u başlat"""
        # Seçili pencereyi al
        selected_hwnd = self.window_combo.currentData()
        
        if selected_hwnd is None:
            self.add_log(secure_strings.get('WINDOW_ALL_SCREEN_WARNING'), "yellow")
        else:
            window_title = self.window_combo.currentText()
            self.add_log(secure_strings.get('WINDOW_TARGET_SELECTED', window_title), "cyan")
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("🟢 AKTIF")
        self.status_label.setStyleSheet("color: #28a745;")
        
        # Tray menü güncelle
        self.tray_start_action.setEnabled(False)
        self.tray_stop_action.setEnabled(True)
        
        self.logger.info(LogCategory.SYS, "═" * 60)
        
        # Ayarları al
        conf = self.conf_spin.value()
        timeout = self.timeout_spin.value()
        model_path = self.model_path_edit.text()
        
        # Model kontrolü
        import os
        if not os.path.exists(model_path):
            self.logger.error(LogCategory.MDL, f"❌ Model dosyası bulunamadı: {model_path}")
            QMessageBox.warning(self, "Hata", f"Model dosyası bulunamadı:\n{model_path}")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        
        self.logger.info(LogCategory.MDL, f"🧠 Model: {model_path}")
        self.logger.info(LogCategory.SYS, f"🎯 Confidence: {conf}")
        self.logger.info(LogCategory.SYS, f"⏱️ Timeout: {timeout}s")
        
        # Thread başlat
        self.bot_thread = BotThread(
            conf_threshold=conf,
            timeout=timeout,
            target_hwnd=selected_hwnd,
            model_path=model_path
        )
        self.bot_thread.log_signal.connect(self.add_log)
        self.bot_thread.stats_signal.connect(self.update_stats)
        self.bot_thread.start()
    
    def stop_bot(self):
        """Bot'u durdur"""
        if self.bot_thread:
            self.bot_thread.stop()
            self.bot_thread.wait(5000)  # 5 saniye timeout
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("⭕ DURDUK")
        self.status_label.setStyleSheet("color: #ff9800;")
        
        # Tray menü güncelle
        self.tray_start_action.setEnabled(True)
        self.tray_stop_action.setEnabled(False)
        
        # İstatistikleri sıfırla
        self.hedef_label.setText("🎯 0")
        self.fps_label.setText("📈 0 FPS")
    
    def add_log_from_logger(self, level, category, message, color):
        """Logger'dan gelen log'u GUI'ye ekle"""
        # HTML formatında ekle
        html = f'<span style="color: {color};">{message}</span>'
        self.log_text.append(html)
        
        # En alta scroll
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def add_log(self, message, color="white"):
        """Eski log fonksiyonu (geriye uyumluluk için)"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Renk map
        color_map = {
            "white": "#ffffff",
            "green": "#00ff00",
            "red": "#ff4444",
            "yellow": "#ffff00",
            "cyan": "#00ffff",
            "gray": "#888888"
        }
        
        hex_color = color_map.get(color, "#ffffff")
        
        # HTML formatında ekle
        html = f'<span style="color: {hex_color};">[{timestamp}] {message}</span>'
        self.log_text.append(html)
        
        # En alta scroll
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def on_log_level_changed(self, level_text):
        """Log level filtresi değişti"""
        level_map = {
            "ALL": -1,  # Tüm loglar
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "CRITICAL": LogLevel.CRITICAL
        }
        
        level = level_map.get(level_text, LogLevel.DEBUG)
        if level == -1:
            self.logger.set_min_level(LogLevel.DEBUG)
        else:
            self.logger.set_min_level(level)
        
        self.logger.info(LogCategory.SYS, f"Log level changed: {level_text}")
    
    def on_auto_save_changed(self, state):
        """Auto-save checkbox değişti"""
        enabled = state == 2  # Qt.CheckState.Checked
        self.logger.set_auto_save(enabled)
        status = "enabled" if enabled else "disabled"
        self.logger.info(LogCategory.SYS, f"Auto-save {status}")
    
    def save_log_manual(self):
        """Manuel log kaydetme"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join("logs", f"manual_save_{timestamp}.txt")
        
        if self.logger.save_to_file(file_path):
            self.logger.info(LogCategory.SYS, f"Log saved: {file_path}")
            QMessageBox.information(self, "✅ Success", f"Log saved:\n{file_path}")
        else:
            self.logger.error(LogCategory.SYS, "Log save failed!")
            QMessageBox.warning(self, "⚠️ Error", "Failed to save log file!")
    
    def clear_log(self):
        """Log ekranını temizle"""
        self.log_text.clear()
        self.logger.clear_buffer()
        self.logger.info(LogCategory.SYS, "Log cleared")
    
    def update_stats(self, stats):
        """İstatistikleri güncelle"""
        self.hedef_label.setText(f"🎯 {stats.get('targets', 0)}")
        self.fps_label.setText(f"📈 {stats.get('fps', 0)} FPS")
    
    def closeEvent(self, event):
        """Pencere kapatılırken bot'u durdur ve config kaydet"""
        # Config'i kaydet
        self.save_config()
        
        # Bot'ı durdur
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot_thread.stop()
            self.bot_thread.wait(5000)
        
        event.accept()

# ==================== MAIN ====================

if __name__ == "__main__":
    # Anti-Debug Protection
    check_debugger()
    
    # VM Detection (sadece uyarı)
    if check_vm():
        print("⚠️ VM detected - Bot may not work properly")
    
    # Memory dump protection
    anti_memory_dump()
    
    # Process obfuscation
    obfuscate_process()
    
    app = QApplication(sys.argv)
    app.setApplicationName("SHIVA BOT")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
