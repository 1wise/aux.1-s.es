<?php
/** Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Initial enrollment requires password reauthentication and a valid first code.
 */
declare(strict_types=1);
define('AUX_ASSIST_ENTRY',true);require __DIR__.'/lib.php';require __DIR__.'/cli-lib.php';
if(($_SERVER['HTTPS']??'')!=='on'){http_response_code(403);exit('HTTPS requerido.');}
header('Cache-Control: no-store');header('Referrer-Policy: no-referrer');
header('X-Content-Type-Options: nosniff');header('X-Robots-Tag: noindex, nofollow');
header("Content-Security-Policy: default-src 'none'; style-src 'self'; font-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
ini_set('session.use_strict_mode','1');ini_set('session.use_only_cookies','1');
session_name('tec_assist');session_set_cookie_params(['secure'=>true,'httponly'=>true,'samesite'=>'Lax','path'=>'/']);session_start();
$_SESSION['csrf']??=bin2hex(random_bytes(32));$err='';$tec=null;$alta=[];
try{
    $tec=cli_auth();
    if($_SERVER['REQUEST_METHOD']==='POST'){
        if((int)($_SERVER['CONTENT_LENGTH']??0)>2048||!is_string($_POST['csrf']??null)||
           !hash_equals($_SESSION['csrf'],$_POST['csrf']))throw new InvalidArgumentException('Formulario caducado.');
        $act=campo($_POST,'action',16);
        if($act==='begin')totp_inicia($tec,campo($_POST,'password',72));
        elseif($act==='confirm'){
            totp_confirma($tec,campo($_POST,'code',6));
            header('Location: cli.php',true,303);exit;
        }elseif($act==='cancel')unset($_SESSION['totp_alta']);
        else throw new InvalidArgumentException('Operación no válida.');
        header('Location: totp.php',true,303);exit;
    }
}catch(Throwable $exc){$err=$exc->getMessage();}
if($tec&&($_SESSION['totp_alta']['id']??'')===$tec['id']&&time()-($_SESSION['totp_alta']['creado']??0)<=300)
    $alta=$_SESSION['totp_alta'];
else unset($_SESSION['totp_alta']);
?>
<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TEC · Configurar segundo factor</title><link rel="stylesheet" href="theme.css"></head><body class="pxe"><main>
<header><a class="logo" href="index.php#cuenta">tec.*</a><h1>Configurar segundo factor</h1></header>
<?php if($err):?><p class="error" role="alert"><?=esc($err)?></p><?php endif?>
<?php if($tec):?>
<?php if(isset($tec['totp_seed'])):?><p>El segundo factor ya está configurado.</p><p><a href="cli.php">Abrir terminal web e introducir el código de seis cifras</a></p><p>Para reemplazar una clave perdida, solicitar el restablecimiento a administración.</p>
<?php elseif($alta):?><section><h2>1. Añadir la cuenta al autenticador</h2>
<p>En Yubico Authenticator: conectar la YubiKey, abrir Accounts y añadir una cuenta manualmente. Guardar estos datos en la aplicación:</p>
<dl><dt>Emisor / Issuer</dt><dd>AUX</dd><dt>Cuenta / Account name</dt><dd><?=esc($tec['correo'])?></dd><dt>Clave secreta / Secret key / Seed</dt><dd><code><?=esc($alta['seed'])?></code></dd><dt>Parámetros</dt><dd>TOTP · SHA-1 · 6 dígitos · 30 segundos</dd></dl>
<p>La clave anterior configura el autenticador. La contraseña de TEC se utiliza para entrar en la cuenta. Esta configuración caduca a los cinco minutos.</p>
<h2>2. Confirmar el código generado</h2><form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>"><input type="hidden" name="action" value="confirm"><label>Código de seis cifras<input name="code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" required></label><button>Activar segundo factor y abrir terminal</button></form>
<form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>"><input type="hidden" name="action" value="cancel"><button>Cancelar configuración</button></form></section>
<?php else:?><p>Para registrar el autenticador de esta cuenta de técnico, confirmar primero la contraseña de TEC.</p><form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>"><input type="hidden" name="action" value="begin"><label>Contraseña de la cuenta TEC<input type="password" name="password" maxlength="72" autocomplete="current-password" required></label><button>Mostrar la clave de configuración del autenticador</button></form><?php endif?>
<?php else:?><p><a href="index.php#cuenta">Entrar con una cuenta de técnico activa y confirmada</a></p><?php endif?>
</main></body></html>
