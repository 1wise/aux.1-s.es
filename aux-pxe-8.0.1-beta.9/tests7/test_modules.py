# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Verify isolated extraction, package contents, and installation plans."""
import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('packages',ROOT/'package-modules.py')
pkg=importlib.util.module_from_spec(spec);spec.loader.exec_module(pkg)


class Modules(unittest.TestCase):
    def test_independent_install_plans_and_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);rows=pkg.empaqueta(out)
            for row in rows:
                arc=out/row['filename'];dst=out/row['module'];dst.mkdir()
                self.assertEqual(hashlib.sha256(arc.read_bytes()).hexdigest(),row['sha256'])
                with zipfile.ZipFile(arc) as z:
                    names=z.namelist()
                    if row['module']=='aux-pxe':
                        self.assertFalse(any(n.startswith(('tec/','cli/')) for n in names))
                        self.assertIn('auxlib/webapps.py',names)
                    else:
                        self.assertIn('tec/web/forum.php',names);self.assertIn('cli/server.py',names)
                        self.assertFalse(any(n.startswith(('auxlib/','ui/')) for n in names))
                    sums=z.read('SHA256SUMS').decode()
                    for line in sums.splitlines():
                        digest,nom=line.split('  ',1);self.assertEqual(hashlib.sha256(z.read(nom)).hexdigest(),digest)
                    z.extractall(dst)
                run=subprocess.run([sys.executable,'install-web.py','--modules',row['module']],cwd=dst,text=True,capture_output=True)
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                self.assertIn('no se modifica',run.stdout.lower())


if __name__=='__main__':unittest.main()
