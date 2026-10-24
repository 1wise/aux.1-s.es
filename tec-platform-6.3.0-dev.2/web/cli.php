<?php
/** Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
 * Author & Credits: https://www.alawise.es/1-s
 * HTML forms remain usable in Links; the interactive terminal requires JavaScript.
 */
declare(strict_types=1);
define('AUX_ASSIST_ENTRY',true);require __DIR__.'/lib.php';require __DIR__.'/cli-lib.php';
$https=($_SERVER['HTTPS']??'')==='on';
if(!$https){http_response_code(403);exit('HTTPS requerido.');}
header('Cache-Control: no-store');header('Referrer-Policy: no-referrer');header('X-Content-Type-Options: nosniff');
session_name('tec_assist');session_set_cookie_params(['secure'=>true,'httponly'=>true,'samesite'=>'Lax','path'=>'/']);session_start();
$_SESSION['csrf']??=bin2hex(random_bytes(32));$err='';$lista=[];$tec=null;$nom='';$url='';
try{
    $tec=cli_auth();$cfg=cli_cfg();$nom=$_POST['node']??$_GET['node']??$cfg['primary'];
    if(!is_string($nom))throw new InvalidArgumentException('CLI inválido.');
    $ent=cli_node($nom);$url=$ent['url'];
    if($_SERVER['REQUEST_METHOD']==='POST'){
        if((int)($_SERVER['CONTENT_LENGTH']??0)>4096||!is_string($_POST['csrf']??null)||!hash_equals($_SESSION['csrf'],$_POST['csrf']))throw new InvalidArgumentException('Formulario caducado.');
        $act=campo($_POST,'action',20);
        if($act==='totp'){cli_totp($tec,campo($_POST,'code',6));header('Location: cli.php?node='.rawurlencode($nom),true,303);exit;}
        cli_lease($tec);
        if($act==='ticket'){
            $id=campo($_POST,'id',32);if(!preg_match('/^[a-f0-9]{32}$/',$id))throw new InvalidArgumentException('Sesión inválida.');
            header('Content-Type: application/json');echo json_encode(['ticket'=>cli_ticket($tec,$nom,'terminal',$id)],JSON_THROW_ON_ERROR);exit;
        }
        if(in_array($act,['claim','close'],true)){
            $id=campo($_POST,'id',32);if(!preg_match('/^[a-f0-9]{32}$/',$id))throw new InvalidArgumentException('Sesión inválida.');
            cli_api($tec,$nom,'/api/sessions/'.$id.'/'.$act,'POST');
            header('Location: cli.php?node='.rawurlencode($nom),true,303);exit;
        }
        if($act==='status'){
            session_write_close();$dat=cli_api($tec,$nom,'/api/sessions');header('Content-Type: application/json');echo json_encode($dat,JSON_THROW_ON_ERROR);exit;
        }
    }
    cli_lease($tec);$lista=cli_api($tec,$nom,'/api/sessions')['sessions'];
}catch(Throwable $exc){$err=$exc->getMessage();if($_SERVER['REQUEST_METHOD']==='POST'&&in_array($_POST['action']??'',['ticket','status'],true)){http_response_code(403);header('Content-Type: application/json');echo json_encode(['error'=>$err]);exit;}}
$connect=$url!==''?' '.str_replace('https://','wss://',$url):'';
header("Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'".$connect."; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
?>
<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TEC · Terminal de asistencia</title><link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="vendor/xterm.css"><script src="vendor/xterm.js" defer></script><script src="cli.js?v=6.3.0-dev.2" defer></script></head><body class="pxe"><main id="cli-app" data-csrf="<?=esc($_SESSION['csrf'])?>" data-node="<?=esc($nom)?>" data-url="<?=esc($url)?>">
<header><a class="logo" href="index.php">tec.*</a><h1>Asistencia · 6.3 de pruebas</h1><p>El cliente debe confirmar el técnico antes de abrir SSH.</p><p><a href="cases.php">Client, USB &amp; case dashboard</a></p></header>
<?php if($err):?><p class="error" role="alert"><?=esc($err)?></p><?php endif?>
<?php if($tec&&!isset($tec['totp_seed'])):?><p><a href="totp.php">Configurar el segundo factor de esta cuenta</a></p><?php endif?>
<?php if($tec):?><form method="get"><label>CLI<select name="node"><?php foreach((config_proyecto()['cli']['nodes']??[]) as $key=>$val):?><option value="<?=esc($key)?>" <?=$key===$nom?'selected':''?>><?=esc($key)?></option><?php endforeach?></select></label><button>Cambiar cli</button></form>
<form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>"><input type="hidden" name="node" value="<?=esc($nom)?>"><input type="hidden" name="action" value="totp"><label>Segundo factor TOTP<input name="code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" required></label><button>Confirmar por 15 minutos</button></form>
<p id="cli-state" role="status">Actualizar para consultar solicitudes. El aviso de escritorio requiere permiso del navegador.</p><button type="button" id="notify-enable">Activar avisos de escritorio</button><a href="cli.php?node=<?=esc($nom)?>">Actualizar solicitudes</a>
<section id="sessions"><h2>Solicitudes</h2><?php foreach($lista as $ses):?><article><h3><?=esc($ses['code'])?></h3><p><?=esc($ses['state'])?></p><form method="post"><input type="hidden" name="csrf" value="<?=esc($_SESSION['csrf'])?>"><input type="hidden" name="node" value="<?=esc($nom)?>"><input type="hidden" name="id" value="<?=esc($ses['id'])?>"><input type="hidden" name="action" value="<?=$ses['state']==='pending'?'claim':'close'?>"><button><?=$ses['state']==='pending'?'Aceptar solicitud':'Cerrar asistencia'?></button></form><?php if($ses['state']==='ready'):?><button type="button" class="terminal-open" data-session="<?=esc($ses['id'])?>">Abrir terminal</button><?php endif?></article><?php endforeach?></section>
<section><h2>Terminal</h2><p>One terminal per case. A persistent USB can reconnect within the approved deadline; use Close assistance to revoke access.</p><p>Para pegar texto, enfoca el campo de terminal y usa el botón cuando la sesión esté autorizada. Para una clave API, espera a la petición de clave y elige entrada visible u oculta antes de pegarla.</p><button type="button" id="terminal-paste" disabled>Pegar desde el portapapeles</button><div id="terminal"></div></section><noscript>Las solicitudes se gestionan con formularios. La terminal interactiva requiere JavaScript.</noscript><?php endif?>
<footer><a href="index.php">Volver a TEC</a> · <a href="https://www.alawise.es/1-s">Créditos, concepto y arquitectura</a></footer></main></body></html>
