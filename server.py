"""Real FTP protocol server, backed by SQLite accounts and transfer history."""
import argparse
import logging
from pathlib import Path
from pyftpdlib.authorizers import DummyAuthorizer, AuthenticationFailed
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from database import DEFAULT_DATA, initialize, connect, verify_user, audit, transfer


def make_handler(data):
    class DatabaseAuthorizer(DummyAuthorizer):
        def validate_authentication(self, username, password, handler):
            if not self.has_user(username) or not verify_user(data, username, password):
                raise AuthenticationFailed('Sai tài khoản hoặc mật khẩu.')

    authorizer = DatabaseAuthorizer()
    with connect(data) as db:
        rows = db.execute('SELECT username,home,permissions FROM users').fetchall()
    if not rows:
        raise ValueError('Chưa có tài khoản. Chạy: python manage.py add-user student')
    for row in rows:
        Path(row['home']).mkdir(parents=True, exist_ok=True)
        authorizer.add_user(row['username'], '', row['home'], perm=row['permissions'])

    class LabHandler(FTPHandler):
        banner = 'Lab 2 FTP ready - SQLite accounts'
        encoding = 'utf-8'

        def record(self, event, detail=''):
            audit(data, self.username or '', self.remote_ip, event, detail)

        def on_connect(self):
            self.record('CONNECT')

        def on_disconnect(self):
            self.record('DISCONNECT')

        def on_login(self, username):
            self.record('LOGIN_OK')

        def on_login_failed(self, username, password):
            audit(data, username, self.remote_ip, 'LOGIN_FAILED', 'Invalid credentials')

        def log_cmd(self, cmd, arg, respcode, respstr):
            super().log_cmd(cmd, arg, respcode, respstr)
            # Never persist passwords, including failed authentication attempts.
            detail = f'{cmd} {"***" if cmd == "PASS" else arg} -> {respcode} {respstr}'
            self.record('COMMAND', detail)

        def on_file_received(self, file):
            transfer(data, self.username, self.remote_ip, 'UPLOAD', file, 'OK')

        def on_file_sent(self, file):
            transfer(data, self.username, self.remote_ip, 'DOWNLOAD', file, 'OK')

        def on_incomplete_file_received(self, file):
            transfer(data, self.username, self.remote_ip, 'UPLOAD', file, 'INCOMPLETE')

        def on_incomplete_file_sent(self, file):
            transfer(data, self.username, self.remote_ip, 'DOWNLOAD', file, 'INCOMPLETE')

    LabHandler.authorizer = authorizer
    return LabHandler


def main():
    p = argparse.ArgumentParser(description='Lab 2 FTP Server (Windows / macOS)')
    p.add_argument('--host', default='0.0.0.0')
    p.add_argument('--port', type=int, default=2121)
    p.add_argument('--data', default=str(DEFAULT_DATA))
    p.add_argument('--passive-start', type=int, default=30000)
    p.add_argument('--passive-end', type=int, default=30049)
    p.add_argument('--advertise-ip', help='IP PASV tùy chọn; thường để trống khi cùng LAN')
    args = p.parse_args()
    if not (1 <= args.port <= 65535 and 1024 <= args.passive_start <= args.passive_end <= 65535):
        p.error('Cổng không hợp lệ (passive phải từ 1024 đến 65535).')
    if args.passive_start <= args.port <= args.passive_end:
        p.error('Cổng điều khiển không được nằm trong dải passive.')
    initialize(args.data)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        handler = make_handler(args.data)
    except ValueError as exc:
        p.error(str(exc))
    handler.passive_ports = range(args.passive_start, args.passive_end + 1)
    handler.masquerade_address = args.advertise_ip
    handler.timeout = 300
    server = FTPServer((args.host, args.port), handler)
    server.max_cons = 100
    server.max_cons_per_ip = 20
    print(f'FTP: {args.host}:{args.port} | PASV: {args.passive_start}-{args.passive_end}', flush=True)
    print(f'Database: {Path(args.data).resolve() / "ftp.sqlite3"}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nĐang dừng server...')
    finally:
        server.close_all()


if __name__ == '__main__':
    main()
