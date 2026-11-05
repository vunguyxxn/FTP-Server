"""Local server administration. Passwords are read without terminal echo."""
import argparse
import getpass
import sqlite3
from database import DEFAULT_DATA, initialize, connect, add_user


def main():
    p = argparse.ArgumentParser(description='Quản lý database FTP Lab 2')
    p.add_argument('--data', default=str(DEFAULT_DATA), help='Thư mục database và dữ liệu')
    sub = p.add_subparsers(dest='command', required=True)
    add = sub.add_parser('add-user')
    add.add_argument('username')
    add.add_argument('--readonly', action='store_true')
    sub.add_parser('users')
    sub.add_parser('logs')
    sub.add_parser('transfers')
    args = p.parse_args()
    initialize(args.data)
    if args.command == 'add-user':
        password = getpass.getpass('Mật khẩu (ít nhất 8 ký tự): ')
        if password != getpass.getpass('Nhập lại mật khẩu: '):
            p.error('Hai mật khẩu không khớp.')
        try:
            add_user(args.data, args.username, password, args.readonly)
        except (ValueError, sqlite3.IntegrityError) as exc:
            p.error(str(exc))
        print('Đã tạo tài khoản. Khởi động lại server để nạp tài khoản mới.')
    else:
        queries = {
            'users': 'SELECT username,permissions,home,created_at FROM users ORDER BY username',
            'logs': 'SELECT * FROM audit ORDER BY id DESC LIMIT 50',
            'transfers': 'SELECT * FROM transfers ORDER BY id DESC LIMIT 50',
        }
        with connect(args.data) as db:
            rows = db.execute(queries[args.command]).fetchall()
        for row in rows:
            print(' | '.join(f'{key}={row[key]}' for key in row.keys()))
        if not rows:
            print('(Chưa có dữ liệu)')


if __name__ == '__main__':
    main()
