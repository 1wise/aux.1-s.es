#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Durable, technician-scoped metadata journal; never record terminal input or keys."""
import json
import os
from pathlib import Path
import sqlite3
import stat
import time


class History:
    def __init__(self, pth=None):
        self.failed = False
        if pth:
            pth = Path(pth)
            try:
                fd = os.open(pth, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                dat = pth.lstat()
                if (not stat.S_ISREG(dat.st_mode) or dat.st_uid != os.geteuid()
                        or dat.st_mode & 0o077 or dat.st_nlink != 1):
                    raise ValueError('History requires a private regular file')
            else:
                os.close(fd)
        self.db = sqlite3.connect(str(pth) if pth else ':memory:')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS events ('
                        'seq INTEGER PRIMARY KEY AUTOINCREMENT, tech TEXT NOT NULL, data TEXT NOT NULL)')
        self.db.execute('CREATE INDEX IF NOT EXISTS events_tech_seq ON events(tech, seq)')
        self.db.commit()

    def append(self, tec_id, dat):
        with self.db:
            self.db.execute('INSERT INTO events(tech,data) VALUES (?,?)',
                            (tec_id, json.dumps(dat, separators=(',', ':'))))

    def read(self, tec_id, cur_evt):
        lst = []
        for seq_evt, dat in self.db.execute(
                'SELECT seq,data FROM events WHERE tech=? AND seq>? ORDER BY seq LIMIT 201',
                (tec_id, cur_evt)):
            lst.append({'seq': seq_evt, **json.loads(dat)})
        may = len(lst) > 200
        lst = lst[:200]
        return {'events': lst, 'cursor': lst[-1]['seq'] if lst else cur_evt, 'more': may,
                'checked_at': int(time.time())}
