<?php
/** Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Validate enrollment, identity binding and replay rejection without a real account.
 */
declare(strict_types=1);
if(PHP_SAPI!=='cli')exit(1);
define('AUX_ASSIST_ENTRY',true);require __DIR__.'/web/lib.php';require __DIR__.'/web/cli-lib.php';
function check(bool $val,string $why):void{if(!$val)throw new RuntimeException($why);}
function rejected(callable $fn,string $why):void{try{$fn();}catch(InvalidArgumentException $exc){return;}throw new RuntimeException($why);}
$_SESSION=['usuario'=>'usr_fixture'];
$usr=['id'=>'usr_fixture','nombre'=>'Test','correo'=>'test@example.test','estado'=>'activo',
      'email_confirmado'=>true,'password_hash'=>password_hash('fixture-password-long',PASSWORD_DEFAULT)];
$tec=['id'=>'tec_fixture','usuario_id'=>'usr_fixture','nombre'=>'Tech','correo'=>$usr['correo'],
      'estado'=>'activo','email_confirmado'=>true];
datos(function(&$dat)use($tec,$usr){$dat['usuarios']=[$usr];$dat['tecnicos']=[$tec];},true);
rejected(fn()=>totp_inicia($tec,'incorrect'),'Wrong password accepted');
totp_inicia($tec,'fixture-password-long');
$alta=$_SESSION['totp_alta'];
check((bool)preg_match('/^[A-Z2-7]{32}$/',$alta['seed']),'Invalid seed');
check(!isset(cli_auth()['totp_seed']),'Unverified seed became active');
$_SESSION['totp_alta']['creado']=time()-301;
rejected(fn()=>totp_confirma($tec,'000000'),'Expired enrollment accepted');
$_SESSION['totp_alta']=$alta;
$_SESSION['totp_alta']['usuario']='other';
rejected(fn()=>totp_confirma($tec,'000000'),'Enrollment accepted for another identity');
$_SESSION['totp_alta']=$alta;
$code=totp_code($alta['seed'],intdiv(time(),30));
totp_confirma($tec,$code);
$act=cli_auth();cli_lease($act);
check(isset($act['totp_seed'])&&!isset($_SESSION['totp_alta']),'Enrollment not committed');
check(!isset(publica($act)['totp_seed']),'Secret leaked into public profile');
rejected(fn()=>cli_totp($act,$code),'Enrollment code reused');
rejected(fn()=>totp_inicia($act,'fixture-password-long'),'Existing seed overwritten');
datos(function(&$dat){$dat['tecnicos'][0]['estado']='suspendido';},true);
rejected(fn()=>totp_confirma($tec,$code),'Suspended account accepted');
echo "PASS: password, pending seed, expiry, identity, activation, replay, privacy and suspension\n";
