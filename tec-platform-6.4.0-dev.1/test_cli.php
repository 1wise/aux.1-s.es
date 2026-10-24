<?php
/** Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Exercise TOTP replay protection and approved-account boundaries in a private fixture.
 */
declare(strict_types=1);
if(PHP_SAPI!=='cli')exit(1);
define('AUX_ASSIST_ENTRY',true);require __DIR__.'/web/lib.php';require __DIR__.'/web/cli-lib.php';
function check(bool $val,string $why):void{if(!$val)throw new RuntimeException($why);}
function rejected(callable $fn,string $why):void{try{$fn();}catch(InvalidArgumentException $exc){return;}throw new RuntimeException($why);}
$_SESSION=[];
$tec=['id'=>'tec_fixture','usuario_id'=>'usr_fixture','nombre'=>'Tech','correo'=>'test@example.test',
      'contacto'=>'https://example.test','estado'=>'activo','email_confirmado'=>true,
      'totp_seed'=>'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'];
$usr=['id'=>'usr_fixture','nombre'=>'Test','correo'=>'test@example.test','estado'=>'activo','email_confirmado'=>true];
datos(function(&$dat)use($tec,$usr){$dat['usuarios']=[$usr];$dat['tecnicos']=[$tec];},true);
$_SESSION['usuario']=$usr['id'];
check(cli_auth()['id']===$tec['id'],'Approved technician can authenticate');
check(totp_code($tec['totp_seed'],1)==='287082','RFC 6238 test vector');
rejected(fn()=>cli_lease($tec),'Missing second factor accepted');
$code=totp_code($tec['totp_seed'],intdiv(time(),30));
cli_totp($tec,$code);cli_lease($tec);
rejected(fn()=>cli_totp($tec,$code),'TOTP replay accepted');
check(!isset(publica($tec)['totp_seed']),'TOTP secret in public profile');
$_SESSION['cli_2fa']=time()-901;
rejected(fn()=>cli_lease($tec),'Expired second factor accepted');
$_SESSION['cli_2fa']=time();$changed=$tec;$changed['totp_seed']='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
rejected(fn()=>cli_lease($changed),'Rotated TOTP seed retained authority');
datos(function(&$dat){$dat['tecnicos'][0]['estado']='suspendido';},true);
rejected(fn()=>cli_auth(),'Suspended technician accepted');
echo "PASS: approved identity, TOTP vector, replay/expiry/rotation, private fields and suspension\n";
