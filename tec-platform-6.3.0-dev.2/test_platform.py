#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Exercise email confirmation and JSON workflows with a fake local sendmail."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--php', default='php')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='aux-assist-test-') as tmp:
        temp = Path(tmp)
        data, key, mailbox = temp / 'private', temp / 'key', temp / 'mailbox.txt'
        sendmail = temp / 'fake-sendmail'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
        sendmail.write_text('#!/bin/sh\ncat >> "$AUX_ASSIST_TEST_MAIL"\nprintf "\\n--MESSAGE--\\n" >> "$AUX_ASSIST_TEST_MAIL"\n')
        sendmail.chmod(0o700)
        env = os.environ | {'AUX_ASSIST_DATA_DIR': str(data), 'AUX_ASSIST_MAIL_FROM': 'assist@example.test',
                            'AUX_ASSIST_PUBLIC_URL': 'https://tec.example.test', 'AUX_ASSIST_ADMIN_MAIL': 'admin@example.test', 'AUX_ASSIST_TEST_MAIL': str(mailbox)}
        driver = temp / 'exercise.php'
        driver.write_text(r'''<?php
define('AUX_ASSIST_ENTRY', true);
require $argv[1] . '/web/lib.php';
function check($ok, $msg) { if (!$ok) { fwrite(STDERR, "FAIL: $msg\n"); exit(1); } }
$row = ['nombre'=>'Técnico Uno','correo'=>'uno@example.test','contacto'=>'https://example.test/uno',
    'telefono'=>'+34 600 123 456','clave'=>trim(file_get_contents($argv[2])),
    'password'=>'cambio-inicial-largo','publicar'=>'si'];
$id = alta_tecnico($row);
$stored = datos(fn($d)=>$d['tecnicos'][0]);
check($stored['estado']==='verificacion_pendiente' && isset($stored['password_hash']), 'technician awaits email confirmation');
check(tecnicos_publicos()===[] && login_tecnico('uno@example.test','cambio-inicial-largo')===null, 'unconfirmed account is private');
try { telefono('abc'); check(false,'malformed phone rejected'); } catch (InvalidArgumentException $e) {}
try { clave_publica('ssh-ed25519 NOT_A_KEY'); check(false,'malformed SSH key rejected'); } catch (InvalidArgumentException $e) {}
$mailbox = getenv('AUX_ASSIST_TEST_MAIL');
preg_match_all('/token=([a-f0-9]{64})/', file_get_contents($mailbox), $matches);
check(count($matches[1])===1 && str_contains(file_get_contents($mailbox),'uno@example.test'), 'technician confirmation email');
reenvia_confirmacion($id);
preg_match_all('/token=([a-f0-9]{64})/', file_get_contents($mailbox), $matches);
check(count($matches[1])===2, 'technician confirmation resend');
try { valida_confirmacion('tecnico',$id,$matches[1][0]); check(false,'resend invalidates old token'); } catch (InvalidArgumentException $e) {}
valida_confirmacion('tecnico',$id,$matches[1][1]);
confirma_email('tecnico',$id,$matches[1][1]);
check(datos(fn($d)=>$d['tecnicos'][0]['estado'])==='pendiente', 'email confirmation still requires manual approval');
try { confirma_email('tecnico',$id,$matches[1][0]); check(false,'confirmation token is single use'); } catch (InvalidArgumentException $e) {}
check(login_tecnico('uno@example.test','cambio-inicial-largo')===null, 'confirmed account still needs admin approval');
$proc = proc_open([$argv[3],'-n',$argv[1].'/manage.php','approve',$id], [['pipe','r'],['pipe','w'],['pipe','w']], $pipes);
fclose($pipes[0]); $out=stream_get_contents($pipes[1]); fclose($pipes[1]); stream_get_contents($pipes[2]); fclose($pipes[2]);
check(proc_close($proc)===0 && str_contains($out,'activo'), 'CLI approves only confirmed technician');
check(login_tecnico('uno@example.test','cambio-inicial-largo')===$id, 'approved login');
check(count(tecnicos_publicos())===1 && tecnicos_publicos()[0]['telefono']==='+34 600 123 456', 'approved public phone');
check(tecnicos_publicos()[0]['correo']==='uno@example.test', 'approved technician email is public');
$sol = alta_solicitud(['tecnico_id'=>$id,'cliente_correo'=>'cliente@example.test','cliente_telefono'=>'+376 312 345',
    'cliente'=>'Cliente A','mensaje'=>'Revisar el arranque']);
$req = datos(fn($d)=>$d['solicitudes'][0]);
check($req['estado']==='confirmacion_pendiente' && $req['cliente_telefono']==='+376 312 345', 'client request waits for email confirmation');
check(solicitudes_tecnico($stored)===[], 'unconfirmed request is hidden from the technician panel');
try { cambia_solicitud($sol, $stored, 'aceptada'); check(false,'unconfirmed request cannot be accepted'); } catch (InvalidArgumentException $e) {}
preg_match_all('/token=([a-f0-9]{64})/', file_get_contents($mailbox), $matches);
check(count($matches[1])===3 && str_contains(file_get_contents($mailbox),'cliente@example.test'), 'client confirmation email');
valida_confirmacion('cliente',$sol,$matches[1][2]);
confirma_email('cliente',$sol,$matches[1][2]);
$req = datos(fn($d)=>$d['solicitudes'][0]);
check($req['email_confirmado'] && $req['estado']==='pendiente', 'confirmed request becomes visible');
check(count(solicitudes_tecnico($stored))===1, 'confirmed request is shown in the technician panel');
check($req['cliente_correo']==='cliente@example.test' && $req['cliente_telefono']==='+376 312 345', 'client contacts stay private');
try { cambia_solicitud($req['id'], ['id'=>'tec_other'], 'aceptada'); check(false,'request ownership enforced'); } catch (InvalidArgumentException $e) {}
cambia_solicitud($req['id'], $stored, 'aceptada');
check(datos(fn($d)=>$d['solicitudes'][0]['estado'])==='aceptada', 'request accepted');
cambia_solicitud($req['id'], $stored, 'cerrada');
check(datos(fn($d)=>$d['solicitudes'][0]['estado'])==='cerrada', 'request closed');
try { cambia_solicitud($req['id'], $stored, 'aceptada'); check(false,'invalid state transition rejected'); } catch (InvalidArgumentException $e) {}

$usr_id=alta_usuario(['nombre'=>'Usuario Cliente','correo'=>'nuevo@example.test','telefono'=>'+376 312 346','password'=>'cuenta-unica-segura']);
check(login_usuario('nuevo@example.test','cuenta-unica-segura')===null,'new user cannot log in before confirmation');
try { alta_usuario(['nombre'=>'Duplicado','correo'=>'uno@example.test','telefono'=>'+376 312 346','password'=>'cuenta-unica-segura']);check(false,'legacy email cannot register twice'); } catch(InvalidArgumentException $e){}
$fake_usr=['id'=>$usr_id,'email_confirmado'=>true,'estado'=>'activo'];
try { solicita_usuario($fake_usr,['tecnico_id'=>$id,'mensaje'=>'spoof']);check(false,'caller cannot spoof confirmed status'); } catch(InvalidArgumentException $e){}
preg_match_all('/token=([a-f0-9]{64})/',file_get_contents($mailbox),$matches);$tok=end($matches[1]);
valida_confirmacion('usuario',$usr_id,$tok);confirma_email('usuario',$usr_id,$tok);
check(login_usuario('nuevo@example.test','cuenta-unica-segura')===$usr_id,'confirmed user login without technician approval');
$_SESSION['usuario']=$usr_id;$usr=usuario_actual();check($usr!==null,'authenticated user loaded');
$sol_usr=solicita_usuario($usr,['tecnico_id'=>$id,'mensaje'=>'Instalación desde cero','cliente_correo'=>'spoof@example.test']);
$own=solicitudes_usuario($usr);check(count($own)===1 && $own[0]['cliente_correo']==='nuevo@example.test','request identity comes from account, not submitted fields');
$tec_new=aplica_tecnico($usr,['url'=>'https://example.test/user','empresa'=>'Empresa A','biografia'=>"Primera línea\nSegunda línea",'clave'=>$row['clave'],'publicar'=>'si']);
check(perfil_usuario($usr)['estado']==='pendiente' && count(tecnicos_publicos())===1,'application waits for review');
datos(function(&$d)use($tec_new){foreach($d['tecnicos'] as &$t)if($t['id']===$tec_new)$t['estado']='activo';},true);
$pub=tecnicos_publicos();check(count($pub)===2,'approved applied profile is public');
check(login_tecnico('nuevo@example.test','cuenta-unica-segura')===$tec_new,'legacy technician login uses canonical user password');
$new_pub=array_values(array_filter($pub,fn($t)=>$t['id']===$tec_new))[0];
foreach(['correo','telefono','url','empresa','biografia'] as $key)check(isset($new_pub[$key]),'full public profile '.$key);
check(!isset($new_pub['password_hash']) && !isset($new_pub['confirm_hash']),'public profile has no credential material');
try { solicita_usuario($usr,['tecnico_id'=>$tec_new,'mensaje'=>'Self']);check(false,'request must target another technician'); } catch(InvalidArgumentException $e){}
contacto_administrador($usr,['mensaje'=>'Contacto al administrador','correo'=>'spoof@example.test']);
$sent=file_get_contents($mailbox);check(str_contains($sent,'admin@example.test')&&str_contains($sent,'Reply-To: nuevo@example.test'),'fixed admin recipient and authenticated reply address');
$forged=['id'=>'usr_missing'];try{contacto_administrador($forged,['mensaje'=>'blocked']);check(false,'anonymous admin mail is forbidden');}catch(InvalidArgumentException $e){}
check(migra_usuarios()===1 && migra_usuarios()===0,'legacy migration is idempotent');
check(login_usuario('uno@example.test','cambio-inicial-largo')!==null,'legacy password survives migration');
try { url_publica('javascript:alert(1)');check(false,'unsafe URL rejected');}catch(InvalidArgumentException $e){}
aplica_tecnico($usr,['url'=>'https://example.test/updated','empresa'=>'Empresa A','biografia'=>'Updated','clave'=>$row['clave'],'publicar'=>'si']);
check(perfil_usuario($usr)['estado']==='pendiente','profile edits go back to review');
echo $id, "\n";
''', encoding='utf-8')
        result = subprocess.run([args.php, '-n', '-d', f'sendmail_path={sendmail}', str(driver), str(root),
                                 str(key.with_suffix('.pub')), args.php], cwd=root, env=env,
                                check=True, capture_output=True, text=True)
        tech_id = result.stdout.strip().splitlines()[-1]
        assert data.stat().st_mode & 0o777 == 0o700
        for name in ('usuarios.json', 'tecnicos.json', 'solicitudes.json'):
            assert (data / name).stat().st_mode & 0o777 == 0o600
        subprocess.run([args.php, '-n', 'manage.php', 'suspend', tech_id], cwd=root, env=env,
                       check=True, capture_output=True, text=True)
        profiles = subprocess.run([args.php, '-n', 'web/profiles.php'], cwd=root, env=env,
                                  check=True, capture_output=True, text=True).stdout
        assert 'Técnico Uno' not in profiles and 'uno@example.test' not in profiles
        assert 'password_hash' not in profiles and 'telefono' not in profiles
        assert json.loads((data / 'tecnicos.json').read_text())[0]['estado'] == 'suspendido'
    print('PASS: unified accounts, confirmation, public profiles, admin mail, migration, CLI approval, private JSON, ownership and suspension')


if __name__ == '__main__':
    main()
