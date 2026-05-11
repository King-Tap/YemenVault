import os
import random
import base64
import secrets 
import string
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.utils import platform

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import arabic_reshaper
from bidi.algorithm import get_display

# استخدام الخط الذي قمت أنت برفه وتغيير اسمه لـ font.ttf
ARABIC_FONT = "font.ttf" 

class MatrixRain(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = []
        Clock.schedule_once(self.init_matrix, 0.1)
        Clock.schedule_interval(self.update_matrix, 0.08)

    def init_matrix(self, dt):
        num_cols = int(Window.width / 40)
        self.cols = [{"x": i * 40, "y": random.randint(0, Window.height), 
                      "speed": random.randint(5, 15)} for i in range(num_cols)]

    def update_matrix(self, dt):
        self.canvas.clear()
        with self.canvas:
            for col in self.cols:
                Color(0, 1, 0, 0.3)
                for i in range(8):
                    Rectangle(pos=(col["x"], col["y"] - (i * 25)), 
                              size=(2, random.randint(10, 20)))
                col["y"] -= col["speed"]
                if col["y"] < -100:
                    col["y"] = Window.height
                    col["speed"] = random.randint(5, 15)

class VaultApp(App):
    def build(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

        root = FloatLayout()
        root.add_widget(MatrixRain())

        main_ui = BoxLayout(orientation='vertical', size_hint=(0.85, 0.8), 
                                 pos_hint={'center_x': 0.5, 'center_y': 0.5}, spacing=20)

        title_lbl = Label(text=self.format_arabic("خزنة البيانات اليمنية"),
                          font_name=ARABIC_FONT, font_size='32sp', color=(0, 1, 0, 1))

        btn_style = {
            'font_name': ARABIC_FONT, 'font_size': '20sp', 'size_hint_y': None,
            'height': '85dp', 'background_normal': '', 'background_color': (0.1, 0.1, 0.1, 0.9)
        }

        # الأزرار
        btns = [
            (self.format_arabic(">> تشفير ملف <<"), (1, 0.2, 0.2, 1), lambda x: self.open_file_browser("encrypt")),
            (self.format_arabic(">> فك التشفير <<"), (0.2, 1, 0.2, 1), lambda x: self.open_file_browser("decrypt")),
            (self.format_arabic(">> منشئ كلمات السر <<"), (0.2, 0.6, 1, 1), self.show_generator_popup)
        ]

        main_ui.add_widget(title_lbl)
        for txt, clr, func in btns:
            b = Button(text=txt, color=clr, **btn_style)
            b.bind(on_release=func)
            main_ui.add_widget(b)
        
        root.add_widget(main_ui)
        return root

    def format_arabic(self, text):
        return get_display(arabic_reshaper.reshape(text))

    def show_generator_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.pwd_display = TextInput(readonly=True, halign='center', font_size='22sp', size_hint_y=None, height='70dp')
        
        gen_btn = Button(text=self.format_arabic("توليد كلمة سر"), font_name=ARABIC_FONT, size_hint_y=None, height='60dp')
        gen_btn.bind(on_release=self.generate_secure_password)
        
        content.add_widget(self.pwd_display)
        content.add_widget(gen_btn)
        self.gen_popup = Popup(title=self.format_arabic("المنشئ الذكي"), content=content, size_hint=(0.9, 0.5))
        self.gen_popup.open()

    def generate_secure_password(self, instance):
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        self.pwd_display.text = ''.join(secrets.choice(alphabet) for i in range(16))

    def open_file_browser(self, mode):
        content = BoxLayout(orientation='vertical')
        file_chooser = FileChooserIconView(path='/sdcard' if platform == 'android' else os.path.expanduser('~'))
        select_btn = Button(text=self.format_arabic("اختيار"), font_name=ARABIC_FONT, size_hint_y=None, height='60dp')
        content.add_widget(file_chooser)
        content.add_widget(select_btn)
        self.fp_popup = Popup(title=self.format_arabic("اختر ملفاً"), content=content, size_hint=(0.95, 0.95))
        select_btn.bind(on_release=lambda x: self.ask_password(file_chooser.selection, mode))
        self.fp_popup.open()

    def ask_password(self, selection, mode):
        if not selection: return
        self.fp_popup.dismiss()
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        pwd_in = TextInput(password=True, multiline=False, size_hint_y=None, height='60dp')
        btn = Button(text=self.format_arabic("تأكيد"), font_name=ARABIC_FONT, size_hint_y=None, height='60dp')
        content.add_widget(pwd_in)
        content.add_widget(btn)
        self.ps_popup = Popup(title=self.format_arabic("كلمة السر"), content=content, size_hint=(0.85, 0.4))
        btn.bind(on_release=lambda x: self.process_file(selection[0], pwd_in.text, mode))
        self.ps_popup.open()

    def process_file(self, path, password, mode):
        self.ps_popup.dismiss()
        try:
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'yemen_salt', iterations=100000)
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            cipher = Fernet(key)
            with open(path, 'rb') as f: data = f.read()
            
            new_path = path + ".yemen" if mode == "encrypt" else path.replace(".yemen", "")
            res = cipher.encrypt(data) if mode == "encrypt" else cipher.decrypt(data)
            
            with open(new_path, 'wb') as f: f.write(res)
            os.remove(path)
            self.show_message("نجاح", "تمت العملية!")
        except:
            self.show_message("خطأ", "فشلت العملية")

    def show_message(self, title, text):
        Popup(title=self.format_arabic(title), content=Label(text=self.format_arabic(text), font_name=ARABIC_FONT), size_hint=(0.7, 0.3)).open()

if __name__ == "__main__":
    VaultApp().run()
