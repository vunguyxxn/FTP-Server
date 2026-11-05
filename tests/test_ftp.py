"""End-to-end tests over real TCP sockets and a temporary SQLite database."""
import concurrent.futures
import ftplib
import hashlib
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database import add_user, connect, verify_user


class FTPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.temp.name)
        add_user(cls.data, 'student', 'DemoPass123!')
        add_user(cls.data, 'viewer', 'ViewerPass123!', readonly=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.log = (cls.data / 'server.log').open('w', encoding='utf-8')
        cls.server = subprocess.Popen([
            sys.executable, str(ROOT / 'server.py'), '--host', '127.0.0.1',
            '--port', str(cls.port), '--data', str(cls.data),
        ], stdout=cls.log, stderr=subprocess.STDOUT)
        for _ in range(100):
            if cls.server.poll() is not None:
                cls.log.close()
                raise RuntimeError((cls.data / 'server.log').read_text(encoding='utf-8'))
            try:
                with socket.create_connection(('127.0.0.1', cls.port), timeout=.2):
                    return
            except OSError:
                time.sleep(.1)
        cls.stop_server()
        raise RuntimeError('Server startup timeout')

    @classmethod
    def stop_server(cls):
        if os.name == 'nt' and cls.server.poll() is None:
            # The Windows venv executable can launch a child Python process.
            # Terminate the test server's own tree, not unrelated Python apps.
            subprocess.run(['taskkill', '/PID', str(cls.server.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        elif cls.server.poll() is None:
            cls.server.terminate()
        cls.server.wait(timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()
        cls.log.close()
        cls.temp.cleanup()

    def ftp(self, username='student', password='DemoPass123!'):
        ftp = ftplib.FTP(timeout=10, encoding='utf-8')
        ftp.connect('127.0.0.1', self.port)
        try:
            ftp.login(username, password)
        except Exception:
            ftp.close()
            raise
        return ftp

    def test_01_authentication(self):
        self.assertTrue(verify_user(self.data, 'student', 'DemoPass123!'))
        with self.assertRaises(ftplib.error_perm):
            self.ftp(password='incorrect')
        with self.assertRaises(ftplib.error_perm):
            self.ftp(username='missing')
        with self.ftp() as ftp:
            self.assertEqual(ftp.pwd(), '/')

    def test_02_binary_unicode_empty_and_crud(self):
        with self.ftp() as ftp:
            ftp.mkd('Bài thực hành')
            ftp.cwd('Bài thực hành')
            for name, payload in [('dữ liệu.bin', os.urandom(2 * 1024 * 1024)), ('empty.txt', b'')]:
                ftp.storbinary('STOR ' + name, io.BytesIO(payload))
                self.assertIn(name, dict(ftp.mlsd()))
                received = io.BytesIO()
                ftp.retrbinary('RETR ' + name, received.write)
                self.assertEqual(hashlib.sha256(payload).digest(), hashlib.sha256(received.getvalue()).digest())
                ftp.rename(name, 'renamed.bin')
                ftp.delete('renamed.bin')
            ftp.cwd('..')
            ftp.rmd('Bài thực hành')

    def test_03_readonly_and_home_isolation(self):
        with self.ftp('viewer', 'ViewerPass123!') as ftp:
            list(ftp.mlsd())
            with self.assertRaises(ftplib.error_perm):
                ftp.mkd('forbidden')
            with self.assertRaises(ftplib.error_perm):
                ftp.storbinary('STOR forbidden.txt', io.BytesIO(b'x'))
            ftp.cwd('../../..')
            self.assertEqual(ftp.pwd(), '/')
            with self.assertRaises(ftplib.error_perm):
                ftp.retrbinary('RETR /../../ftp.sqlite3', lambda data: None)

    def test_04_six_clients(self):
        def worker(index):
            payload = os.urandom(128 * 1024)
            with self.ftp() as ftp:
                name = f'parallel-{index}.bin'
                ftp.storbinary('STOR ' + name, io.BytesIO(payload))
                received = io.BytesIO()
                ftp.retrbinary('RETR ' + name, received.write)
                ftp.delete(name)
                return received.getvalue() == payload
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            self.assertTrue(all(pool.map(worker, range(6))))

    def test_05_database_persistence(self):
        with self.ftp() as ftp:
            ftp.storbinary('STOR database-check.txt', io.BytesIO(b'database evidence'))
            ftp.retrbinary('RETR database-check.txt', lambda data: None)
        # Transfer callbacks are delivered by the server immediately after 226.
        for _ in range(30):
            with connect(self.data) as db:
                rows = db.execute("SELECT * FROM transfers WHERE path LIKE '%database-check.txt'").fetchall()
            if len(rows) >= 2:
                break
            time.sleep(.05)
        self.assertEqual({row['direction'] for row in rows}, {'UPLOAD', 'DOWNLOAD'})
        self.assertTrue(all(row['bytes'] == 17 and row['status'] == 'OK' for row in rows))
        with connect(self.data) as db:
            serialized = '\n'.join(str(tuple(row)) for row in db.execute('SELECT * FROM audit'))
            user = db.execute("SELECT * FROM users WHERE username='student'").fetchone()
        self.assertNotIn('DemoPass123!', serialized)
        self.assertNotEqual(user['password_hash'], 'DemoPass123!')
        self.assertIn('LOGIN_OK', serialized)
        self.assertIn('LOGIN_FAILED', serialized)

    def test_06_active_mode(self):
        # The bundled GUI uses passive; the server also interoperates with active clients.
        with self.ftp() as ftp:
            ftp.set_pasv(False)
            list(ftp.mlsd())


if __name__ == '__main__':
    unittest.main(verbosity=2)
