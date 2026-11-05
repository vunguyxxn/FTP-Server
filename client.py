"""Cross-platform Tk FTP client. All socket work uses a single background worker."""
import ftplib
import os
from pathlib import Path, PurePosixPath
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


class LoggedFTP(ftplib.FTP):
    def __init__(self, emit):
        self.emit = emit
        super().__init__(timeout=20, encoding='utf-8')

    def putcmd(self, line):
        self.emit('log', '> PASS ********' if line.upper().startswith('PASS ') else '> ' + line)
        return super().putcmd(line)

    def getresp(self):
        response = super().getresp()
        self.emit('log', '< ' + response)
        return response


class Client(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Lab 2 • FTP Explorer')
        self.geometry('1120x760')
        self.minsize(880, 620)
        self.ftp = None  # Owned exclusively by the worker thread.
        self.connected = False
        self.busy = False
        self.events = queue.Queue()
        self.local_path = Path.home()
        self.remote_path = '/'
        self.remote_items = {}
        self.status = tk.StringVar(value='Chưa kết nối • FTP passive / UTF-8')
        self.progress = tk.DoubleVar(value=0)
        self._ui()
        self.local_refresh()
        self.after(80, self.poll)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

    def emit(self, kind, value):
        self.events.put((kind, value))

    def _ui(self):
        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('Treeview', rowheight=28)
        style.configure('Title.TLabel', font=('Arial', 19, 'bold'))
        root = ttk.Frame(self, padding=16)
        root.pack(fill='both', expand=True)
        ttk.Label(root, text='FTP Explorer', style='Title.TLabel').pack(anchor='w')
        ttk.Label(root, text='LAB 02  /  Windows ↔ macOS  /  Server + SQLite').pack(anchor='w', pady=(2, 12))
        bar = ttk.Frame(root)
        bar.pack(fill='x')
        self.host = tk.StringVar(value='127.0.0.1')
        self.port = tk.StringVar(value='2121')
        self.user = tk.StringVar(value='student')
        self.password = tk.StringVar()
        self.entries = []
        for col, (label, variable, width, secret) in enumerate([
            ('Host / IP server', self.host, 23, False), ('Port', self.port, 7, False),
            ('Tài khoản', self.user, 15, False), ('Mật khẩu', self.password, 18, True),
        ]):
            cell = ttk.Frame(bar)
            cell.grid(row=0, column=col, padx=(0, 10), sticky='w')
            ttk.Label(cell, text=label).pack(anchor='w')
            entry = ttk.Entry(cell, textvariable=variable, width=width, show='*' if secret else '')
            entry.pack()
            self.entries.append(entry)
        self.connect_btn = ttk.Button(bar, text='Kết nối', command=self.connect_server)
        self.connect_btn.grid(row=0, column=4, sticky='s', padx=4)
        self.disconnect_btn = ttk.Button(bar, text='Ngắt', command=self.disconnect)
        self.disconnect_btn.grid(row=0, column=5, sticky='s')
        ttk.Separator(root).pack(fill='x', pady=12)
        panes = ttk.Panedwindow(root, orient='horizontal')
        panes.pack(fill='both', expand=True)
        left, right = ttk.Frame(panes), ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=1)
        self.local_label = ttk.Label(left, text='', wraplength=460)
        self.local_label.pack(anchor='w', pady=6)
        self.remote_label = ttk.Label(right, text='SERVER • Chưa kết nối', wraplength=460)
        self.remote_label.pack(anchor='w', pady=6)
        local_bar = ttk.Frame(left)
        local_bar.pack(fill='x', pady=(0, 6))
        ttk.Button(local_bar, text='Chọn thư mục', command=self.choose_local).pack(side='left')
        ttk.Button(local_bar, text='↑ Thư mục cha', command=self.local_up).pack(side='left', padx=4)
        ttk.Button(local_bar, text='Làm mới', command=self.local_refresh).pack(side='left')
        remote_bar = ttk.Frame(right)
        remote_bar.pack(fill='x', pady=(0, 6))
        self.remote_buttons = []
        for text, command in [('↑ Thư mục cha', lambda: self.change_remote('..')),
                              ('Làm mới', self.remote_refresh), ('Tạo thư mục', self.mkdir)]:
            button = ttk.Button(remote_bar, text=text, command=command)
            button.pack(side='left', padx=(0, 4))
            self.remote_buttons.append(button)
        self.local_tree = self.tree(left)
        self.remote_tree = self.tree(right)
        self.local_tree.bind('<Double-1>', self.open_local)
        self.remote_tree.bind('<Double-1>', self.open_remote)
        actions = ttk.Frame(root)
        actions.pack(fill='x', pady=10)
        for text, command in [('Tải lên →', self.upload), ('← Tải xuống', self.download),
                              ('Đổi tên trên server', self.rename), ('Xóa trên server', self.delete)]:
            button = ttk.Button(actions, text=text, command=command)
            button.pack(side='left', padx=(0, 8))
            self.remote_buttons.append(button)
        ttk.Progressbar(root, variable=self.progress, maximum=100).pack(fill='x')
        ttk.Label(root, textvariable=self.status).pack(anchor='w', pady=6)
        ttk.Label(root, text='NHẬT KÝ GIAO THỨC • USER / PASV / MLSD / STOR / RETR').pack(anchor='w')
        self.log = tk.Text(root, height=7, bg='#142333', fg='#d7e5f5', font=('Consolas', 10), state='disabled')
        self.log.pack(fill='x', pady=(5, 0))
        self.controls()

    def tree(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=(0, 6))
        tree = ttk.Treeview(frame, columns=('kind', 'size'), selectmode='browse')
        tree.heading('#0', text='Tên file / thư mục')
        tree.heading('kind', text='Loại')
        tree.heading('size', text='Bytes')
        tree.column('#0', width=240, minwidth=120)
        tree.column('kind', width=70, stretch=False)
        tree.column('size', width=95, anchor='e', stretch=False)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        tree.pack(side='left', fill='both', expand=True)
        return tree

    def controls(self):
        self.connect_btn.configure(state='disabled' if self.busy or self.connected else 'normal')
        self.disconnect_btn.configure(state='normal' if self.connected and not self.busy else 'disabled')
        for button in self.remote_buttons:
            button.configure(state='normal' if self.connected and not self.busy else 'disabled')
        for entry in self.entries:
            entry.configure(state='disabled' if self.busy or self.connected else 'normal')

    def run_job(self, label, job):
        if self.busy:
            return
        self.busy = True
        self.progress.set(0)
        self.status.set(label)
        self.controls()

        def worker():
            try:
                job()
                self.emit('status', 'Hoàn tất • ' + label)
            except Exception as exc:
                # A failed data operation can leave a control reply pending.
                # Close rather than reuse a potentially desynchronized session.
                if self.ftp:
                    self.ftp.close()
                    self.ftp = None
                self.emit('connected', False)
                self.emit('error', str(exc))
            finally:
                self.emit('done', None)

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'log':
                    self.log.configure(state='normal')
                    self.log.insert('end', value + '\n')
                    if int(self.log.index('end-1c').split('.')[0]) > 1000:
                        self.log.delete('1.0', '100.0')
                    self.log.see('end')
                    self.log.configure(state='disabled')
                elif kind == 'connected':
                    self.connected = value
                    if not value:
                        self.remote_tree.delete(*self.remote_tree.get_children())
                        self.remote_items.clear()
                        self.remote_label.configure(text='SERVER • Chưa kết nối')
                elif kind == 'listing':
                    self.remote_path, listing = value
                    self.remote_tree.delete(*self.remote_tree.get_children())
                    self.remote_items.clear()
                    for name, facts in sorted(listing, key=lambda x: (x[1].get('type') != 'dir', x[0].lower())):
                        if facts.get('type') in ('cdir', 'pdir'):
                            continue
                        kind_name = 'Thư mục' if facts.get('type') == 'dir' else 'File'
                        iid = self.remote_tree.insert('', 'end', text=name, values=(kind_name, facts.get('size', '')))
                        self.remote_items[iid] = (name, facts.get('type') == 'dir')
                    self.remote_label.configure(text='SERVER • ' + self.remote_path)
                elif kind == 'progress':
                    self.progress.set(value)
                elif kind == 'status':
                    self.status.set(value)
                elif kind == 'local':
                    self.local_refresh()
                elif kind == 'error':
                    self.status.set('Lỗi • Đã đóng kết nối. Kiểm tra nhật ký và kết nối lại.')
                    messagebox.showerror('FTP', value)
                elif kind == 'done':
                    self.busy = False
                    self.controls()
        except queue.Empty:
            pass
        self.after(80, self.poll)

    def list_remote(self):
        self.emit('listing', (self.ftp.pwd(), list(self.ftp.mlsd())))

    def connect_server(self):
        host, user, password = self.host.get().strip(), self.user.get().strip(), self.password.get()
        try:
            port = int(self.port.get())
            if not host or not user or not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            messagebox.showerror('Kết nối', 'Nhập host, tài khoản và cổng 1–65535.')
            return

        def job():
            self.ftp = LoggedFTP(self.emit)
            self.ftp.connect(host, port)
            self.ftp.login(user, password)
            self.ftp.set_pasv(True)
            self.list_remote()
            self.emit('connected', True)
        self.run_job('Kết nối ' + host, job)

    def disconnect(self):
        def job():
            try:
                self.ftp.quit()
            finally:
                self.ftp.close()
                self.ftp = None
                self.emit('connected', False)
        self.run_job('Ngắt kết nối', job)

    def local_refresh(self):
        self.local_tree.delete(*self.local_tree.get_children())
        self.local_label.configure(text='MÁY CỦA BẠN • ' + str(self.local_path))
        try:
            for path in sorted(self.local_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                try:
                    self.local_tree.insert('', 'end', text=path.name,
                                           values=('Thư mục' if path.is_dir() else 'File', '' if path.is_dir() else path.stat().st_size))
                except OSError:
                    continue
        except OSError as exc:
            messagebox.showerror('Thư mục local', str(exc))

    def choose_local(self):
        path = filedialog.askdirectory(initialdir=self.local_path)
        if path:
            self.local_path = Path(path)
            self.local_refresh()

    def local_up(self):
        self.local_path = self.local_path.parent
        self.local_refresh()

    def open_local(self, event=None):
        selected = self.local_tree.selection()
        if selected:
            path = self.local_path / self.local_tree.item(selected[0], 'text')
            if path.is_dir():
                self.local_path = path
                self.local_refresh()

    def remote_selection(self):
        selected = self.remote_tree.selection()
        return self.remote_items.get(selected[0]) if selected else None

    def open_remote(self, event=None):
        selected = self.remote_selection()
        if selected and selected[1]:
            self.change_remote(selected[0])

    def change_remote(self, path):
        if self.connected and not self.busy:
            def job():
                self.ftp.cwd(path)
                self.list_remote()
            self.run_job('Mở thư mục ' + path, job)

    def remote_refresh(self):
        self.run_job('Làm mới server', self.list_remote)

    @staticmethod
    def valid_name(name):
        return bool(name and name not in ('.', '..') and not any(c in name for c in '/\\\r\n\x00'))

    def progress_callback(self, total):
        count = 0
        last_percent = -1
        def callback(block):
            nonlocal count, last_percent
            count += len(block)
            percent = min(100, int(count * 100 / total)) if total else 100
            if percent != last_percent:
                self.emit('progress', percent)
                last_percent = percent
        return callback

    def upload(self):
        selected = self.local_tree.selection()
        if not selected:
            return
        path = self.local_path / self.local_tree.item(selected[0], 'text')
        if not path.is_file():
            messagebox.showinfo('Tải lên', 'Chọn một file. Thư mục có thể tạo bằng nút Tạo thư mục.')
            return
        if not self.valid_name(path.name):
            messagebox.showerror('Tên file', 'Tên file không hợp lệ cho FTP.')
            return
        if any(item[0] == path.name for item in self.remote_items.values()):
            if not messagebox.askyesno('Ghi đè', f'Ghi đè {path.name} trên server?'):
                return
        def job():
            callback = self.progress_callback(path.stat().st_size)
            with path.open('rb') as stream:
                self.ftp.storbinary('STOR ' + path.name, stream, 65536, callback)
            self.emit('progress', 100)
            self.list_remote()
        self.run_job('Tải lên ' + path.name, job)

    def download(self):
        selected = self.remote_selection()
        if not selected or selected[1]:
            return
        name = selected[0]
        # A remote server must not be able to write outside the chosen local directory.
        if not self.valid_name(name) or PurePosixPath(name).name != name:
            messagebox.showerror('Tên file', 'Tên file từ server không an toàn.')
            return
        destination = self.local_path / name
        if destination.exists() and not messagebox.askyesno('Ghi đè', f'Ghi đè file local {name}?'):
            return
        def job():
            self.ftp.voidcmd('TYPE I')
            total = self.ftp.size(name) or 0
            callback = self.progress_callback(total)
            fd, temp_path = tempfile.mkstemp(prefix='.ftp-', suffix='.part', dir=destination.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    def receive(block):
                        stream.write(block)
                        callback(block)
                    self.ftp.retrbinary('RETR ' + name, receive, 65536)
                os.replace(temp_path, destination)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            self.emit('progress', 100)
            self.emit('local', None)
        self.run_job('Tải xuống ' + name, job)

    def mkdir(self):
        name = simpledialog.askstring('Tạo thư mục', 'Tên thư mục trên server:', parent=self)
        if name is None:
            return
        if not self.valid_name(name):
            messagebox.showerror('Tên thư mục', 'Tên không được chứa /, \\, xuống dòng hoặc là . / ..')
            return
        def job():
            self.ftp.mkd(name)
            self.list_remote()
        self.run_job('Tạo thư mục ' + name, job)

    def rename(self):
        selected = self.remote_selection()
        if not selected:
            return
        name = simpledialog.askstring('Đổi tên', 'Tên mới:', initialvalue=selected[0], parent=self)
        if name is None:
            return
        if not self.valid_name(name):
            messagebox.showerror('Đổi tên', 'Tên không hợp lệ.')
            return
        if any(item[0] == name for item in self.remote_items.values()):
            messagebox.showerror('Đổi tên', 'Tên đã tồn tại trên server. Chọn tên khác.')
            return
        def job():
            self.ftp.rename(selected[0], name)
            self.list_remote()
        self.run_job('Đổi tên ' + selected[0], job)

    def delete(self):
        selected = self.remote_selection()
        if not selected or not messagebox.askyesno('Xóa', f'Xóa {selected[0]}? Thư mục phải rỗng.'):
            return
        def job():
            (self.ftp.rmd if selected[1] else self.ftp.delete)(selected[0])
            self.list_remote()
        self.run_job('Xóa ' + selected[0], job)


if __name__ == '__main__':
    Client().mainloop()
