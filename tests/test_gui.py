"""Exercise real Tk widgets and GUI upload/download against the test FTP server."""
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import Client
from test_ftp import FTPIntegration


def main():
    FTPIntegration.setUpClass()
    app = Client()
    errors = []
    def wait():
        deadline = time.monotonic() + 15
        while app.busy:
            app.update()
            if time.monotonic() > deadline:
                raise TimeoutError('GUI worker timeout')
            time.sleep(.02)
        app.update()
        assert not errors, errors

    try:
        with patch('client.messagebox.showerror', side_effect=lambda *args: errors.append(args)):
            app.port.set(str(FTPIntegration.port))
            app.password.set('DemoPass123!')
            app.connect_server()
            wait()
            assert app.connected
            local = FTPIntegration.data / 'gui-local'
            local.mkdir()
            sample = local / 'GUI tiếng Việt.txt'
            sample.write_bytes(b'GUI upload and download\x00\xff')
            app.local_path = local
            app.local_refresh()
            item = next(i for i in app.local_tree.get_children() if app.local_tree.item(i, 'text') == sample.name)
            app.local_tree.selection_set(item)
            app.upload()
            wait()
            original = sample.read_bytes()
            sample.unlink()
            item = next(i for i, entry in app.remote_items.items() if entry[0] == sample.name)
            app.remote_tree.selection_set(item)
            app.download()
            wait()
            assert sample.read_bytes() == original
            app.disconnect()
            wait()
            assert not app.connected
        print('PASS: Tk render, connect, Unicode upload/download, disconnect')
    finally:
        if app.ftp:
            app.ftp.close()
        app.destroy()
        FTPIntegration.tearDownClass()


if __name__ == '__main__':
    main()
