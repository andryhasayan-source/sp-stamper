# -*- coding: utf-8 -*-
"""
ShashevPro Stamper — приватная утилита авторских меток.

НЕ ДЛЯ ПУБЛИКАЦИИ. Ставит в файл бота две метки:
  • видимую  — обычный комментарий (например, «# shashevpro»);
  • скрытую  — подпись, закодированную невидимыми символами Юникода.

Метки кладутся в комментарии и в позиции вне строк (после top-level «}»),
поэтому код не ломается, а невидимые символы не попадают в текст бота.
Скрытая метка ставится один раз (повторно не дублируется).
Кнопка «Копировать скрытую метку» кладёт невидимые символы в буфер —
их можно вставить в файл вручную (лучше всего внутрь комментария).

Запуск:  python sp_stamper.py
"""
import os
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

# ── Палитра (тёмная тема) ────────────────────────────────────────────
BG = "#0b0f14"
BG2 = "#121a24"
BG3 = "#1a2430"
BG3_HI = "#222e3c"
CARD = "#151d27"
INP = "#0e151d"
BDR = "#22303f"
TEXT = "#e7eef6"
DIM = "#8497ab"
MUTE = "#5a6b80"
VK = "#2f88ff"
VK_HI = "#57a0ff"
OK = "#3fb950"
OK_HI = "#46c95a"
WARN = "#d6a531"
WARN_HI = "#e3b545"
UI = "Segoe UI"

# ── Скрытая метка: 4 невидимых символа = 2 бита каждый ───────────────
_ZW = ["\u200b", "\u200c", "\u200d", "\u2060"]
_ZW_IDX: dict[str, int] = {}
for _i, _c in enumerate(_ZW):
    _ZW_IDX[_c] = _i

# legacy-префикс: НЕ добавляется в новые метки. Срезается при чтении
# старых файлов (см. detect_stamp), чтобы сохранить совместимость.
MAGIC = "SPX1"


def resource_path(name: str) -> Path:
    """Путь к ресурсу и при обычном запуске, и внутри PyInstaller --onefile."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / name
    return Path(__file__).resolve().parent / name


def zw_encode(text: str) -> str:
    """Кодирует строку в последовательность невидимых символов."""
    out: list[str] = []
    for byte in text.encode("utf-8"):
        out.append(_ZW[(byte >> 6) & 3])
        out.append(_ZW[(byte >> 4) & 3])
        out.append(_ZW[(byte >> 2) & 3])
        out.append(_ZW[byte & 3])
    return "".join(out)


def zw_decode(zw: str) -> str | None:
    """Декодирует невидимые символы обратно в строку (или None)."""
    vals: list[int] = []
    for ch in zw:
        if ch in _ZW_IDX:
            vals.append(_ZW_IDX[ch])
    usable = (len(vals) // 4) * 4
    out = bytearray()
    i = 0
    while i < usable:
        byte = ((vals[i] << 6) | (vals[i + 1] << 4)
                | (vals[i + 2] << 2) | vals[i + 3])
        out.append(byte)
        i += 4
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return None


def read_source(path: str | Path) -> str:
    """Читает файл (utf-8 → cp1251) и лечит переводы строк до \\n."""
    data = Path(path).read_bytes()
    text: str | None = None
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = data.decode("utf-8", errors="replace")
    text = re.sub(r"\r+\n", "\n", text)
    return text.replace("\r", "\n")


def write_source(path: str | Path, text: str) -> None:
    """Пишет файл строго в LF (без трансляции переводов строк)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    Path(path).write_bytes(text.encode("utf-8"))


def detect_stamp(src: str) -> str | None:
    """Возвращает скрытую подпись, если в файле найден корректный zw-блок.

    Блоком считается непрерывная цепочка невидимых символов, длина которой
    кратна 4 (наша кодировка — 4 символа на байт) и которая декодируется
    в печатаемый непустой текст. Старый префикс «SPX1|», если встретится,
    срезается ради совместимости с ранее помеченными файлами.
    """
    for run in re.findall(r"[\u200b\u200c\u200d\u2060]+", src):
        if len(run) < 4 or len(run) % 4:
            continue
        decoded = zw_decode(run)
        if not decoded or not decoded.strip() or not decoded.isprintable():
            continue
        if decoded.startswith(MAGIC + "|"):       # старый формат метки
            decoded = decoded[len(MAGIC) + 1:]
        return decoded
    return None


def stamp_source(src: str, visible: str, hidden: str) -> tuple[str, bool]:
    """Ставит РОВНО одну видимую и РОВНО одну скрытую метку.

    Args:
        src: исходный текст файла.
        visible: текст видимого комментария (например, «# shashevpro»).
        hidden: произвольная скрытая подпись (например, «shashevpro.ru»).

    Returns:
        (новый_текст, добавлено?). Если скрытая метка уже была — текст
        не меняется и второй элемент False.
    """
    if detect_stamp(src) is not None:
        return src, False

    visible = visible.strip()
    if not visible.startswith("#"):
        visible = "# " + visible
    zw = zw_encode(hidden)          # чистая подпись, без служебного префикса
    carrier_mid = "#" + zw          # на вид пустой комментарий
    carrier_end = "# cfg" + zw      # на вид служебный комментарий

    anchors = [m.end() for m in re.finditer(r"(?m)^\}[ \t]*$", src)]
    inserts: list[tuple[int, str]] = []
    hidden_in_body = False
    if anchors:
        inserts.append((anchors[0], "\n" + visible))          # видимая
        if len(anchors) >= 2:
            inserts.append((anchors[1], "\n" + carrier_mid))  # скрытая в теле
            hidden_in_body = True
    for pos, piece in sorted(inserts, key=lambda x: -x[0]):
        src = src[:pos] + piece + src[pos:]

    tail = ""
    if not src.endswith("\n"):
        tail += "\n"
    if not anchors:                       # нет якорей — видимую в конец
        tail += visible + "\n"
    if not hidden_in_body:                # скрытая — РОВНО один раз: в конец,
        tail += carrier_end + "\n"        # только если она не легла в тело
    return src + tail, True


# ── Интерфейс ────────────────────────────────────────────────────────
class App:
    """Окно утилиты: загрузить → метка → сохранить."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.src_path: str | None = None
        self.current: str = ""

        root.title("ShashevPro Stamper")
        root.configure(bg=BG)
        root.geometry("780x600")
        root.minsize(680, 520)

        self._build_toolbar()
        self._build_settings()
        self._build_preview()
        self._build_status()
        self._build_footer()

    # — построение —
    def _btn(self, parent: tk.Misc, text: str, cmd, bg: str,
             hov: str, fg: str = "white") -> tk.Button:
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                      font=(UI, 10, "bold"), relief="flat", bd=0,
                      padx=16, pady=8, cursor="hand2",
                      activebackground=hov, activeforeground=fg,
                      highlightthickness=0)
        b.bind("<Enter>", lambda e: b.configure(bg=hov), add=True)
        b.bind("<Leave>", lambda e: b.configure(bg=bg), add=True)
        return b

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self.root, bg=BG2)
        bar.pack(fill="x")
        inner = tk.Frame(bar, bg=BG2)
        inner.pack(side="left", padx=14, pady=12)
        self._btn(inner, "Загрузить", self.load, VK, VK_HI).pack(
            side="left", padx=4)
        self._btn(inner, "Метка", self.mark, WARN, WARN_HI, fg=BG).pack(
            side="left", padx=4)
        self._btn(inner, "Сохранить", self.save, OK, OK_HI).pack(
            side="left", padx=4)

    def _build_settings(self) -> None:
        wrap = tk.Frame(self.root, bg=CARD)
        wrap.pack(fill="x", padx=14, pady=(4, 8))
        tk.Label(wrap, text="  Настройки меток", bg=CARD, fg=TEXT,
                 font=(UI, 10, "bold")).pack(anchor="w", padx=10, pady=(10, 6))

        self.visible_var = tk.StringVar(value="# shashevpro")
        self.hidden_var = tk.StringVar(value="shashevpro.ru")
        self._field(wrap, "Видимая метка:", self.visible_var,
                    "обычный комментарий, виден в коде")
        self._field(wrap, "Скрытая подпись:", self.hidden_var,
                    "кодируется невидимыми символами")

        row = tk.Frame(wrap, bg=CARD)
        row.pack(fill="x", padx=10, pady=(6, 2))
        tk.Frame(row, bg=CARD, width=16).pack(side="left")   # отступ под поля
        self._btn(row, "Копировать скрытую метку", self.copy_mark,
                  BG3, BG3_HI, fg=TEXT).pack(side="left", padx=4)
        tk.Label(row, text="невидимые символы — вставьте в комментарий",
                 bg=CARD, fg=MUTE, font=(UI, 8)).pack(side="left", padx=6)
        tk.Frame(wrap, bg=CARD, height=8).pack()

    def _field(self, parent: tk.Misc, label: str, var: tk.StringVar,
               hint: str) -> None:
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=10, pady=4)
        tk.Label(row, text=label, bg=CARD, fg=DIM, font=(UI, 9),
                 width=16, anchor="w").pack(side="left")
        ent = tk.Entry(row, textvariable=var, bg=INP, fg=TEXT,
                       insertbackground=TEXT, relief="flat", font=(UI, 9),
                       bd=0, highlightthickness=1, highlightcolor=VK,
                       highlightbackground=BDR, width=34)
        ent.pack(side="left", ipady=5, padx=4)
        tk.Label(row, text=hint, bg=CARD, fg=MUTE,
                 font=(UI, 8)).pack(side="left", padx=6)

    def _build_preview(self) -> None:
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        tk.Label(wrap, text="Предпросмотр файла", bg=BG, fg=DIM,
                 font=(UI, 8, "bold")).pack(anchor="w", pady=(0, 4))
        self.preview = scrolledtext.ScrolledText(
            wrap, bg=INP, fg=TEXT, insertbackground=TEXT,
            font=("Consolas", 9), relief="flat", wrap="none", bd=0,
            highlightthickness=1, highlightcolor=BDR, highlightbackground=BDR,
            padx=8, pady=6)
        self.preview.pack(fill="both", expand=True)
        self.preview.insert("1.0", "Откройте файл бота кнопкой «Загрузить».")
        self.preview.configure(state="disabled")

    def _build_status(self) -> None:
        self.status = tk.Label(self.root, text="  Готов к работе",
                               bg=BG3, fg=DIM, font=(UI, 8), anchor="w")
        self.status.pack(fill="x", ipady=4)

    def _build_footer(self) -> None:
        ft = tk.Frame(self.root, bg=BG2, height=26)
        ft.pack(fill="x")
        ft.pack_propagate(False)
        tk.Label(ft, text="© 2026  ShashevPro", bg=BG2, fg=DIM,
                 font=(UI, 8, "bold")).pack(side="left", padx=14)
        tk.Label(ft, text="shashevpro.ru  •  programmer@shashevpro.ru",
                 bg=BG2, fg=MUTE, font=(UI, 8)).pack(side="right", padx=14)

    # — действия —
    def _set_preview(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def _say(self, text: str) -> None:
        self.status.configure(text="  " + text)

    def load(self) -> None:
        """Открывает файл бота и показывает его в предпросмотре."""
        path = filedialog.askopenfilename(
            title="Открыть файл бота",
            filetypes=[("Python", "*.py"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            self.current = read_source(path)
        except OSError as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
            return
        self.src_path = path
        self._set_preview(self.current)
        existing = detect_stamp(self.current)
        if existing is not None:
            self._say(f"Загружен: {Path(path).name} — уже помечен "
                      f"(«{existing}»)")
        else:
            self._say(f"Загружен: {Path(path).name}")

    def mark(self) -> None:
        """Ставит метки в загруженный файл (в памяти)."""
        if not self.src_path:
            messagebox.showwarning("Нет файла", "Сначала загрузите файл.")
            return
        visible = self.visible_var.get().strip()
        hidden = self.hidden_var.get().strip()
        if not visible or not hidden:
            messagebox.showwarning(
                "Пустые поля",
                "Заполните видимую метку и скрытую подпись.")
            return
        result, added = stamp_source(self.current, visible, hidden)
        if not added:
            messagebox.showinfo(
                "Метка уже есть",
                "В файле уже стоит скрытая метка — повторно не добавляю.\n"
                "Чтобы поставить другую, загрузите исходный (чистый) файл.")
            return
        self.current = result
        self._set_preview(result)
        self._say("Метки поставлены — не забудьте «Сохранить»")

    def copy_mark(self) -> None:
        """Кодирует скрытую подпись и кладёт невидимые символы в буфер."""
        hidden = self.hidden_var.get().strip()
        if not hidden:
            messagebox.showwarning("Пустое поле",
                                   "Заполните скрытую подпись.")
            return
        payload = zw_encode(hidden)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(payload)
            self.root.update()            # зафиксировать буфер в системе
        except tk.TclError as e:
            messagebox.showerror("Ошибка",
                                 f"Не удалось обратиться к буферу:\n{e}")
            return
        self._say(f"Скрытая метка в буфере — {len(payload)} невидимых симв.")
        messagebox.showinfo(
            "Скопировано",
            "Скрытая метка скопирована в буфер обмена.\n\n"
            "Символы невидимы. Куда вставлять:\n"
            "•  в комментарий — самый безопасный вариант;\n"
            "•  на отдельной строке — поставьте перед меткой «#»;\n"
            "•  в строковый литерал, который НЕ уходит пользователю.\n\n"
            "Не вставляйте в текст, который бот шлёт людям, —\n"
            "иначе невидимые символы попадут в сообщения.\n\n"
            f"При расшифровке покажет:  {hidden}")

    def save(self) -> None:
        """Сохраняет текущий текст (с метками) на диск."""
        if not self.src_path:
            messagebox.showwarning("Нет файла", "Сначала загрузите файл.")
            return
        suggested = Path(self.src_path).name
        path = filedialog.asksaveasfilename(
            title="Сохранить файл бота",
            defaultextension=".py", initialfile=suggested,
            filetypes=[("Python", "*.py"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            write_source(path, self.current)
        except OSError as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")
            return
        self._say(f"Сохранено: {Path(path).name}")
        messagebox.showinfo("Готово", f"Файл сохранён:\n{path}")


def _enable_dpi() -> None:
    """Чёткий рендеринг на мониторах с масштабированием (Windows)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except OSError:
            ctypes.windll.user32.SetProcessDPIAware()
    except (ImportError, AttributeError, OSError):
        pass


def main() -> None:
    _enable_dpi()
    root = tk.Tk()
    try:
        root.iconbitmap(str(resource_path("icon.ico")))
    except tk.TclError:
        pass  # иконки нет — окно с системной, не критично
    try:
        root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72.0)
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())
