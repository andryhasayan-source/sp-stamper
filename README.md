# SP Stamper · ShashevPro

### Утилита авторских меток для Python-файлов · Authorship watermark tool for Python files

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat)
![Source](https://img.shields.io/badge/source-open-brightgreen?style=flat)

---

Ставит в Python-файл две авторских метки одновременно — видимую и скрытую. Видимая метка — обычный комментарий в коде. Скрытая — подпись, закодированная невидимыми символами Юникода, незаметная при просмотре файла.

Stamps two authorship marks into a Python file simultaneously — a visible comment and a hidden Unicode steganography signature invisible to the naked eye.

---

## 🖥 Screenshot

![SP Stamper](screenshots/1.png)

---

## ✨ Как работает · How it works

**Видимая метка** — вставляется как обычный комментарий в начало файла:
```python
# shashevpro
```

**Скрытая метка** — строка (например, `shashevpro.ru`) кодируется в невидимые символы Unicode (`\u200b`, `\u200c`, `\u200d`, `\u2060`) и вставляется в комментарий. При просмотре файла метка не видна, но поддаётся декодированию.

- Скрытая метка ставится один раз — повторная обработка файла не дублирует её
- Кнопка **«Копировать скрытую метку»** копирует невидимые символы в буфер — их можно вставить в любой комментарий вручную
- Код файла не ломается — метки размещаются только в комментариях

---

## 🚀 Запуск · Run

```bash
python sp_stamper.py
```

Requires Python 3.8+. No external dependencies — standard library only (tkinter).

---

## 📦 Сборка EXE · Build EXE

```bash
pip install pyinstaller
build_stamper.bat
```

или вручную:

```bash
pyinstaller --onefile --windowed --name "SP_Stamper" --icon "icon.ico" --add-data "icon.ico;." sp_stamper.py
```

Ready `.exe` is available in [Releases](../../releases).

---

## 📁 Файлы · Files

```
├── sp_stamper.py       # Main application
├── build_stamper.bat   # Build script
├── SP_Stamper.spec     # PyInstaller spec
└── icon.ico            # Application icon
```

---

## 🌐 Author

**Andrey Shashev · ShashevPro**

- 🌐 [shashevpro.ru](https://www.shashevpro.ru)
- 🛒 [kwork.ru/user/shashevpro](https://kwork.ru/user/shashevpro)
- 💬 [vk.com/andrey_shashev](https://vk.com/andrey_shashev)
- ✉️ programmer@shashevpro.ru

---

*MIT License · © ShashevPro*
