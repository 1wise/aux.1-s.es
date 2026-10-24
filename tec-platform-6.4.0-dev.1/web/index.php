<?php
/** Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * One confirmed account serves clients and technician applications; forms work in Links.
 */
declare(strict_types=1);
define('AUX_ASSIST_ENTRY',true); require __DIR__.'/lib.php';
$vista=($_GET['view']??'')==='pxe'?'pxe':'aux'; $base='index.php?view='.$vista;
$https=($_SERVER['HTTPS']??'')==='on';
$local=in_array($_SERVER['REMOTE_ADDR']??'',['127.0.0.1','::1'],true)&&getenv('AUX_ASSIST_LOCAL_TEST')==='1';
if(!$https&&!$local){header('Location: '.rtrim(config_tec('public_url','AUX_ASSIST_PUBLIC_URL','https://tec.1-s.es'),'/').'/'.$base,true,303);exit;}
header('Cache-Control: no-store');header('X-Content-Type-Options: nosniff');header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'none'; style-src 'self'; font-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
ini_set('session.use_strict_mode','1');ini_set('session.use_only_cookies','1');
session_name('tec_assist');session_set_cookie_params(['secure'=>$https,'httponly'=>true,'samesite'=>'Lax','path'=>'/']);session_start();
$_SESSION['csrf']??=bin2hex(random_bytes(32));
$err='';$msg=$_SESSION['aviso']??'';unset($_SESSION['aviso']);$usr=null;$perfil=null;$tec=null;$lista=[];$sol=[];$propias=[];$confirmacion=null;
try{
 $usr=usuario_actual();$perfil=$usr?perfil_usuario($usr):null;$tec=$perfil&&$perfil['estado']==='activo'?$perfil:null;
 if($_SERVER['REQUEST_METHOD']==='POST'){
  if((int)($_SERVER['CONTENT_LENGTH']??0)>16384)throw new InvalidArgumentException('Formulario demasiado grande.');
  if(!is_string($_POST['csrf']??null)||!hash_equals($_SESSION['csrf'],$_POST['csrf']))throw new InvalidArgumentException('Formulario caducado. Recargar antes de enviar.');
  $act=campo($_POST,'accion',30);
  if($act==='alta'){limita('alta');alta_usuario($_POST);$msg='Registro recibido. Confirmar el correo con el enlace enviado para activar la cuenta.';}
  elseif($act==='login'){
   limita('login');$id=login_usuario(correo(campo($_POST,'correo',254)),campo($_POST,'password',72));
   if(!$id)throw new InvalidArgumentException('Credenciales incorrectas o correo sin confirmar/cuenta inactiva.');
   session_regenerate_id(true);$_SESSION['usuario']=$id;unset($_SESSION['tecnico'],$_SESSION['cli_2fa'],$_SESSION['cli_2fa_tec'],$_SESSION['cli_2fa_seed'],$_SESSION['totp_alta']);$msg='Sesión iniciada.';
  }elseif($act==='salir'){unset($_SESSION['usuario'],$_SESSION['tecnico'],$_SESSION['cli_2fa'],$_SESSION['cli_2fa_tec'],$_SESSION['cli_2fa_seed'],$_SESSION['totp_alta']);session_regenerate_id(true);$msg='Sesión cerrada.';}
  elseif($act==='confirmar'){confirma_email(campo($_POST,'tipo',16),campo($_POST,'id',40),campo($_POST,'token',64));$msg='Correo confirmado. Entrar con la cuenta registrada; las solicitudes de técnico requieren aprobación.';}
  elseif($act==='aplicar'&&$usr){limita('aplicar');aplica_tecnico($usr,$_POST);$msg='Perfil recibido. Queda pendiente de revisión manual antes de publicarse.';}
  elseif($act==='solicitud'&&$usr){limita('solicitud');solicita_usuario($usr,$_POST);$msg='Solicitud registrada para el técnico seleccionado. No activa SSH ni VPN.';}
  elseif($act==='contacto'&&$usr){limita('contacto');contacto_administrador($usr,$_POST);$msg='El MTA aceptó el mensaje para administración. Esto no garantiza su llegada al buzón.';}
  elseif($act==='estado'&&$tec){cambia_solicitud(campo($_POST,'id',40),$tec,campo($_POST,'estado',20));$msg='Estado actualizado.';}
  else throw new InvalidArgumentException('Iniciar sesión para esta operación.');
  $_SESSION['csrf']=bin2hex(random_bytes(32));$_SESSION['aviso']=$msg;header('Location: '.$base,true,303);exit;
 }
 if(isset($_GET['confirm'],$_GET['id'],$_GET['token'])){
  $tp=campo($_GET,'confirm',16);$id=campo($_GET,'id',40);$tok=campo($_GET,'token',64);valida_confirmacion($tp,$id,$tok);$confirmacion=['tipo'=>$tp,'id'=>$id,'token'=>$tok];
 }
 $lista=tecnicos_publicos();if($usr)$propias=solicitudes_usuario($usr);if($tec)$sol=solicitudes_tecnico($tec);
}catch(InvalidArgumentException $e){http_response_code(400);$err=$e->getMessage();}
catch(Throwable $e){error_log('TEC unavailable: '.$e->getMessage());http_response_code(503);$err='Plataforma no disponible. Revisar configuración, directorio privado y MTA.';}
function ocultos(string $act):void{echo '<input type="hidden" name="csrf" value="'.esc($_SESSION['csrf']).'"><input type="hidden" name="accion" value="'.esc($act).'">';}
function campo_html(string $nom,string $titulo,string $tipo='text',int $max=100,bool $req=true,string $valor=''):void{
 echo '<label>'.esc($titulo).'<input name="'.esc($nom).'" type="'.esc($tipo).'" maxlength="'.$max.'" value="'.esc($valor).'" '.($req?'required':'').' autocomplete="'.($tipo==='password'?'off':'on').'"></label>';
}
$cfg=config_proyecto();$aux=$cfg['base_url']??'https://aux.1-s.es';$pxe=$cfg['pxe_url']??'http://pxe.1-s.es';
?>
<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>TEC · Usuarios, técnicos y asistencia</title><link rel="stylesheet" href="theme.css"></head><body class="<?=esc($vista)?>"><main>
<header><a class="logo" href="<?=esc($base)?>">tec.*</a><p>Usuarios · técnicos · asistencia · <?=esc(ASIST_VERSION)?></p>
<nav><a href="<?=esc($aux)?>/">aux./</a> <a href="<?=esc($pxe)?>/"><span class="pxe-wordmark">PXE&gt;<span class="pxe-cursor">_</span></span></a> <a href="#directorio">Técnicos</a> <a href="#cuenta">Cuenta</a> <a href="#solicitud">Asistencia</a> <a href="#aplicar">Solicitar rol de técnico</a> <a href="#contacto">Administración</a> <a href="index.php?view=pxe">Vista terminal</a></nav></header>
<?php if($err):?><p class="error" role="alert"><?=esc($err)?></p><?php endif?>
<?php if($msg):?><p class="notice" role="status"><?=esc($msg)?></p><?php endif?>
<?php if($confirmacion):?><section><h1>Confirmar correo</h1><p>El enlace no confirma por sí solo: usar el botón. Válido una vez durante 24 horas.</p><form method="post" action="<?=esc($base)?>"><?php ocultos('confirmar');foreach($confirmacion as $k=>$v):?><input type="hidden" name="<?=esc($k)?>" value="<?=esc($v)?>"><?php endforeach?><button>Confirmar correo</button></form></section><?php endif?>
<section id="directorio"><h1>Técnicos disponibles</h1><p>Perfiles aprobados. Cada persona puede solicitar asistencia a otro técnico desde su cuenta.</p>
<?php if(!$lista):?><p>No hay técnicos activos publicados.</p><?php endif?>
<?php foreach($lista as $ent):?><article id="<?=esc($ent['id'])?>"><h2><?=esc($ent['nombre'])?></h2><dl><dt>Email</dt><dd><a href="mailto:<?=esc($ent['correo'])?>"><?=esc($ent['correo'])?></a></dd><dt>Teléfono</dt><dd><a href="tel:<?=esc($ent['telefono'])?>"><?=esc($ent['telefono'])?></a></dd><dt>URL</dt><dd><?php if($ent['url']??''):?><a href="<?=esc($ent['url'])?>" rel="noopener noreferrer"><?=esc($ent['url'])?></a><?php else:?>Pendiente de completar<?php endif?></dd><dt>Empresa</dt><dd><?=esc($ent['empresa']??'Pendiente de completar')?></dd></dl><h3>Biografía</h3><p><?=nl2br(esc($ent['biografia']??'Pendiente de completar'))?></p><details><summary>Clave pública SSH / <?=esc($ent['id'])?></summary><pre><?=esc($ent['clave'])?></pre></details></article><?php endforeach?></section>
<section id="cuenta"><h2>Cuenta única</h2>
<?php if($tec):?><p><a href="cases.php">Client, USB &amp; case dashboard</a></p><?php endif?>
<?php if($tec && (config_proyecto()['cli']['enabled']??false)===true):?><p><a href="cli.php">Terminal web · solicitudes y avisos</a> · <a href="totp.php">Configurar segundo factor</a></p><?php endif?>
<?php if($usr):?><p><?=esc($usr['nombre'])?> · <?=esc($usr['correo'])?></p><form method="post" action="<?=esc($base)?>"><?php ocultos('salir');?><button>Cerrar sesión</button></form>
<?php else:?><h3>Entrar</h3><form method="post" action="<?=esc($base)?>"><?php ocultos('login');campo_html('correo','Email','email',254);campo_html('password','Contraseña','password',72);?><button>Entrar</button></form>
<details open><summary>Registrar usuario</summary><p>Confirmar el correo activa la cuenta para solicitar asistencia y contactar con administración. Los datos de una cuenta de usuario no se publican en el directorio; se publicará el perfil profesional cuando se solicite y apruebe.</p><form method="post" action="<?=esc($base)?>"><?php ocultos('alta');campo_html('nombre','Nombre');campo_html('correo','Email','email',254);campo_html('telefono','Teléfono','tel',32);campo_html('password','Contraseña de 12 a 72 bytes','password',72);?><button>Registrar cuenta</button></form></details><?php endif?></section>
<section id="solicitud"><h2>Pedir asistencia o una instalación</h2>
<?php if(!$usr):?><p><a href="#cuenta">Entrar o registrarse</a> para pedir asistencia.</p><?php elseif(!$lista):?><p>No hay técnicos disponibles.</p><?php else:?><form method="post" action="<?=esc($base)?>"><?php ocultos('solicitud');?><label>Técnico<select name="tecnico_id" required><?php foreach($lista as $ent):?><option value="<?=esc($ent['id'])?>"><?=esc($ent['nombre'])?></option><?php endforeach?></select></label><p>Contacto: <?=esc($usr['nombre'])?> · <?=esc($usr['correo'])?> · <?=esc($usr['telefono'])?></p><label>Mensaje / instalación solicitada<textarea name="mensaje" rows="5" maxlength="4000" required></textarea></label><button>Pedir asistencia</button></form><h3>Solicitudes propias</h3><?php foreach(array_reverse($propias) as $ent):?><article><p><?=esc($ent['id'])?> · <?=esc($ent['estado'])?></p><p><?=nl2br(esc($ent['mensaje']))?></p></article><?php endforeach?><?php endif?></section>
<section id="aplicar"><h2>Perfil de técnico</h2>
<?php if(!$usr):?><p>Se utiliza la misma cuenta de usuario.</p><?php else:?><p>Estado: <?=esc($perfil['estado']??'sin solicitud')?>. El email y teléfono serán los de la cuenta. El alta y las modificaciones requieren revisión antes de publicar.</p><form method="post" action="<?=esc($base)?>"><?php ocultos('aplicar');campo_html('url','URL profesional','url',500,true,$perfil['url']??'');campo_html('empresa','Empresa / proyecto','text',150,true,$perfil['empresa']??'');?><label>Biografía<textarea name="biografia" rows="5" maxlength="4000" required><?=esc($perfil['biografia']??'')?></textarea></label><label>Clave pública SSH<textarea name="clave" rows="3" maxlength="12000" required><?=esc($perfil['clave']??'')?></textarea></label><label class="check"><input type="checkbox" name="publicar" value="si" required>Publicar email, teléfono, URL, empresa, biografía y clave pública del perfil profesional bajo CC BY-NC-SA 4.0.</label><button>Enviar perfil a revisión</button></form><?php endif?></section>
<?php if($tec):?><section><h2>Panel del técnico</h2><?php if(!$sol):?><p>No hay solicitudes.</p><?php endif?><?php foreach(array_reverse($sol) as $ent):?><article><h3><?=esc($ent['cliente'])?></h3><p><a href="mailto:<?=esc($ent['cliente_correo'])?>"><?=esc($ent['cliente_correo'])?></a> · <?=esc($ent['cliente_telefono'])?></p><p><?=nl2br(esc($ent['mensaje']))?></p><p><?=esc($ent['estado'])?></p><?php foreach(['pendiente'=>['aceptada'=>'Aceptar','rechazada'=>'Rechazar'],'aceptada'=>['cerrada'=>'Cerrar']][$ent['estado']]??[] as $estado=>$label):?><form method="post" action="<?=esc($base)?>"><?php ocultos('estado');?><input type="hidden" name="id" value="<?=esc($ent['id'])?>"><input type="hidden" name="estado" value="<?=esc($estado)?>"><button><?=esc($label)?></button></form><?php endforeach?></article><?php endforeach?></section><?php endif?>
<section id="contacto"><h2>Contactar con administración</h2><?php if(!$usr):?><p>Disponible al entrar con una cuenta confirmada.</p><?php else:?><form method="post" action="<?=esc($base)?>"><?php ocultos('contacto');?><label>Mensaje<textarea name="mensaje" rows="5" maxlength="4000" required></textarea></label><button>Enviar correo al administrador</button></form><?php endif?></section>
<footer>CopyLeft 03/2026 · Créditos, Concepto y arquitectura en <a href="https://www.alawise.es/1-s">alawise.es/1-s</a><br>Contenidos publicados bajo licencia <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons CC BY-NC-SA 4.0</a>.</footer></main></body></html>
