# Timestamp: 2026-11-09 | Version: 7.0.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Check publishing invariants, native plans and privileged destination handling."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from auxlib import catalog, common, enter, profiles, setup


def entrada(**campos):
    dat = {'id':'debian-one', 'family':'debian', 'release':'testing-20261109',
           'architecture':'amd64', 'kind':'installer', 'download_class':'light',
           'original_url':'https://cdimage.debian.org/sample.iso', 'sha256':'a' * 64}
    dat.update(campos)
    return dat


class Catalogo(unittest.TestCase):
    def test_rechaza_urls_no_https_credenciales_y_controles(self):
        for url in ('http://example.org/a.iso', 'https://a:b@example.org/a', 'https://example.org/a\nboot', 'https://example.org/a;reboot'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                catalog.url_segura(url)

    def test_los_hosts_se_comparan_completos(self):
        with self.assertRaises(ValueError):
            catalog.url_segura('https://cdimage.debian.org.evil.invalid/a', ['cdimage.debian.org'])

    def test_clase_se_declara_sin_umbral_inventado(self):
        with self.assertRaises(ValueError):
            catalog.valida(entrada(download_class='automatic'))
        self.assertEqual(catalog.valida(entrada(size_bytes=9999999999))['download_class'], 'light')

    def test_no_entra_pxe_sin_prueba_de_arranque(self):
        ent = entrada(boot={'kernel_url':'https://example.org/k','initrd_url':'https://example.org/i','kernel_args':['ip=dhcp']})
        self.assertIsNone(catalog.receta(ent, {}))
        pru = {ent['id']:{'identity':catalog.identidad(ent),'deployed_urls':'passed','bios_boot':'passed'}}
        self.assertIn('kernel https://example.org/k', catalog.receta(ent, pru))
        ent['release'] = 'changed'
        self.assertIsNone(catalog.receta(ent, pru))

    def test_receta_rechaza_inyeccion_ipxe(self):
        ent = entrada(boot={'kernel_url':'https://example.org/k','initrd_url':'https://example.org/i','kernel_args':['ip=dhcp\nreboot']})
        pru = {ent['id']:{'identity':catalog.identidad(ent),'deployed_urls':'passed','uefi_boot':'passed'}}
        with self.assertRaises(ValueError):
            catalog.receta(ent, pru)

    def test_publicacion_nueva_conserva_anterior(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            a = catalog.publica([entrada()], raiz)
            b = catalog.publica([entrada(release='next')], raiz)
            self.assertNotEqual(a, b)
            self.assertTrue(a.is_dir())
            self.assertEqual((raiz/'current').resolve(), b)
            self.assertEqual(json.loads((b/'catalog.json').read_text())['entries'][0]['release'], 'next')
            self.assertTrue(b.stat().st_mode & 0o005)

    def test_descarga_fallida_no_cambia_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            previo = catalog.publica([entrada()], raiz)
            with patch.object(catalog, 'descarga', side_effect=OSError('incomplete')):
                with self.assertRaises(OSError):
                    catalog.publica([entrada(release='next')], raiz, descargar=True,
                                    politica={'enabled':True,'ids':['debian-one'],'max_images':1,'max_total_bytes':1024})
            self.assertEqual((raiz/'current').resolve(), previo)
            self.assertEqual(len(list((raiz/'releases').iterdir())), 1)

    def test_actualizacion_invalida_no_borra_catalogo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            previo = catalog.publica([entrada()], raiz)
            with self.assertRaises(ValueError):
                catalog.publica([], raiz)
            self.assertEqual((raiz/'current').resolve(), previo)

    def test_identificadores_duplicados_rechazados(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            catalog.publica([entrada(), entrada()], Path(tmp))

    def test_clasificaciones_y_html_escapado(self):
        with tempfile.TemporaryDirectory() as tmp:
            ent = entrada(family='<script>alert(1)</script>')
            dst = catalog.publica([ent], Path(tmp))
            self.assertIn(ent['original_url'], (dst/'light-url.txt').read_text())
            self.assertNotIn(ent['original_url'], (dst/'heavy-url.txt').read_text())
            self.assertNotIn('<script>alert(1)</script>', (dst/'index.html').read_text())
            self.assertNotIn('kernel ', (dst/'menu.ipxe').read_text())

    def test_manifiestos_gnu_y_fedora(self):
        txt = 'a'*64 + '  one.iso\nSHA256 (two.iso) = ' + 'b'*64 + '\n'
        self.assertEqual(catalog.parsea_sumas(txt), {'one.iso':'a'*64, 'two.iso':'b'*64})
        with self.assertRaises(ValueError):
            catalog.parsea_sumas(txt + 'c'*64 + '  one.iso\n')

    def test_adaptador_html_une_solo_candidatos_de_fuente(self):
        fuente = {'id':'debian','url':'https://cdimage.debian.org/index/','allowed_hosts':['cdimage.debian.org'],
                  'format':'html','pattern':r'debian-(?P<release>[0-9.]+)-(?P<architecture>amd64)\.iso',
                  'defaults':{'family':'debian','kind':'installer','download_class':'light'}}
        def traer(url, hosts, cache):
            return b'<a href="debian-13.3-amd64.iso">icon</a><a href="debian-13.3-amd64.iso">ok</a><a href="../README">other</a>'
        ent = catalog.descubre(fuente, Path('/unused'), traer)
        self.assertEqual(len(ent),1)
        self.assertEqual(ent[0]['release'],'13.3')
        self.assertEqual(ent[0]['architecture'],'amd64')

    def test_fuente_vacia_es_error_y_no_un_catalogo_vacio(self):
        fuente = {'id':'x','url':'https://example.org/','allowed_hosts':['example.org'],
                  'format':'html','pattern':r'.*\.iso','defaults':{}}
        with self.assertRaises(ValueError):
            catalog.descubre(fuente, Path('/unused'), lambda *args:b'<html>maintenance</html>')


class Perfiles(unittest.TestCase):
    def test_mismo_rol_paquetes_nativos_distintos(self):
        fed = profiles.seleccion('fedora',['disks'])
        deb = profiles.seleccion('debian',['disks'])
        self.assertIn('ddrescue',fed['packages'])
        self.assertIn('gddrescue',deb['packages'])
        self.assertNotIn('gddrescue',fed['packages'])

    def test_roles_no_se_omiten_silenciosamente(self):
        with self.assertRaises(ValueError):
            profiles.seleccion('debian',['unknown'])

    def test_instaladores_no_borran_discos_automaticamente(self):
        with tempfile.TemporaryDirectory() as tmp:
            for dis,nom in [('fedora','installed.ks'),('debian','preseed.cfg')]:
                dst = Path(tmp)/dis
                profiles.genera(dis,['base','network'],dst)
                txt = (dst/nom).read_text()
                for prohibido in ('clearpart','zerombr','partman-auto/method','partman/confirm boolean true'):
                    self.assertNotIn(prohibido,txt)
                self.assertEqual(json.loads((dst/'selection.json').read_text())['repository_check'],'not-run')

    def test_falta_de_paquete_aborta_antes_de_generar(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(profiles,'verifica',side_effect=ValueError('missing')):
            with self.assertRaises(ValueError):
                profiles.genera('debian',['base'],Path(tmp)/'out',True)
            self.assertFalse((Path(tmp)/'out').exists())

    def test_iso_incluye_instalacion_de_las_aplicaciones(self):
        with tempfile.TemporaryDirectory() as tmp:
            for dis,nom in [('fedora','installed.ks'),('debian','preseed.cfg')]:
                dst=Path(tmp)/dis
                profiles.genera(dis,['base'],dst,build_id='a'*32)
                txt=(dst/nom).read_text()
                self.assertIn('sha256sum -c SHA256SUMS',txt)
                self.assertIn('--mode tools',txt)
                self.assertIn('a'*32,txt)

    def test_marcador_iso_no_admite_shell(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            profiles.genera('fedora',['base'],Path(tmp),build_id='x; reboot')


class Instalacion(unittest.TestCase):
    def test_raiz_nueva_nunca_puede_ser_host(self):
        with self.assertRaises(ValueError):
            setup.comandos_base('debian',Path('/'),True,['base'],'testing')

    def test_base_debian_usa_debootstrap_y_firmware(self):
        cmd = setup.comandos_base('debian',Path('/tmp/new-root'),True,['base'],'testing')[0]
        self.assertEqual(cmd[0],'debootstrap')
        self.assertIn('--components=main,contrib,non-free,non-free-firmware',cmd)
        self.assertIn('/tmp/new-root',cmd)

    def test_base_fedora_fija_release_y_repositorio(self):
        cmd = setup.comandos_base('fedora',Path('/tmp/new-root'),True,['base'],'rawhide')[0]
        self.assertIn('--releasever=rawhide',cmd)
        self.assertIn('--enablerepo=rawhide',cmd)

    def test_instalacion_en_raiz_temporal_es_repetible(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            setup.instala_archivos(raiz)
            cfg=raiz/'etc/aux-assist/cli.json'
            cfg.write_text('{"custom":true}')
            setup.instala_archivos(raiz)
            self.assertEqual(cfg.read_text(),'{"custom":true}')
            self.assertTrue((raiz/'usr/local/lib/aux/auxlib/setup.py').is_file())
            self.assertTrue((raiz/'usr/local/bin/aux-setup').is_symlink())
            self.assertEqual((raiz/'var/lib/aux-assist/install.json').stat().st_mode & 0o777,0o600)
            uni=(raiz/'etc/systemd/system/aux-assist.service').read_text()
            self.assertNotIn('tech-work',uni)
            self.assertNotIn('nm-online',uni)
            self.assertFalse((raiz/'etc/systemd/system/aux-observer@.service').exists())

    def test_escapes_por_enlace_rechazados(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp)/'root'
            raiz.mkdir()
            (raiz/'etc').symlink_to('/etc')
            with self.assertRaises(ValueError):
                common.dentro(raiz,'etc/aux-installed')

    def test_cli_plan_no_necesita_root_ni_ejecuta_gestor(self):
        res = subprocess.run(['python3',str(common.DIR_APP/'aux-setup'),'--mode','existing','--distro','debian','--roles','base'],capture_output=True,text=True)
        self.assertEqual(res.returncode,0,res.stderr)
        self.assertIn('+ apt-get update',res.stdout)


class Entrada(unittest.TestCase):
    def test_modos_de_inspeccion_no_reproducen_journal(self):
        self.assertEqual(enter.opciones('ext4',False),'ro,noload')
        self.assertEqual(enter.opciones('xfs',False),'ro,norecovery')
        self.assertEqual(enter.opciones('btrfs',False),'ro,nologreplay')
        self.assertEqual(enter.opciones('ext4',True),'rw')

    def test_formato_no_admitido_no_se_monta(self):
        with self.assertRaises(ValueError):
            enter.opciones('ntfs',False)

    def test_desmontaje_en_orden_inverso(self):
        with patch.object(enter.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as cmd:
            enter.limpia(['/root','/root/dev','/root/dev/pts'])
        self.assertEqual([llamada.args[0][-1] for llamada in cmd.call_args_list],['/root/dev/pts','/root/dev','/root'])

    def test_montaje_ocupado_no_se_oculta_con_lazy_unmount(self):
        with patch.object(enter.subprocess,'run',return_value=subprocess.CompletedProcess([],1)) as cmd:
            with self.assertRaises(RuntimeError):
                enter.limpia(['/root','/root/dev'])
            self.assertEqual(cmd.call_count,1)
            self.assertNotIn('-l',cmd.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
