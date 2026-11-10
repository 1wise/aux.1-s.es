<?php
/** Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Keep cli secrets and TOTP seeds exclusively in private server storage.
 */
declare(strict_types=1);
if (!defined('AUX_ASSIST_ENTRY')) { http_response_code(404); exit; }

function cli_cfg(): array {
    $cfg=config_proyecto()['cli']??[];
    if (($cfg['enabled']??false)!==true) throw new RuntimeException('La pasarela no está habilitada en este servidor.');
    return $cfg;
}
function cli_node(string $nom): array {
    $cfg=cli_cfg(); $ent=$cfg['nodes'][$nom]??null;
    if (!is_array($ent)) throw new InvalidArgumentException('CLI desconocido.');
    foreach(['url','secret_file'] as $key) if(!is_string($ent[$key]??null)) throw new RuntimeException('Configuración de cli incompleta.');
    $url=parse_url($ent['url']);
    if(($url['scheme']??'')!=='https'||isset($url['user'])||isset($url['pass'])||isset($url['query'])||isset($url['fragment'])||!empty($url['path']))
        throw new RuntimeException('CLI requiere origen HTTPS sin ruta ni credenciales.');
    return $ent;
}
function cli_ticket(array $tec,string $nom,string $scope,string $ses=''): string {
    $ent=cli_node($nom);$sec=@file_get_contents($ent['secret_file']);
    if($sec===false||strlen(trim($sec))<32)throw new RuntimeException('Secreto del cli ausente o inválido.');
    $dat=['aud'=>$nom,'sub'=>$tec['id'],'scope'=>$scope,'session'=>$ses,
          'name'=>$tec['nombre'],'contact'=>$tec['contacto']??$tec['correo'],
          'direct_key'=>$tec['clave']??'',
          'exp'=>time()+60,'nonce'=>bin2hex(random_bytes(24))];
    $b64=fn(string $txt)=>rtrim(strtr(base64_encode($txt),'+/','-_'),'=');
    $pay=$b64(json_encode($dat,JSON_THROW_ON_ERROR));
    return $pay.'.'.$b64(hash_hmac('sha256',$pay,trim($sec),true));
}
function cli_api(array $tec,string $nom,string $path,string $method='GET'): array {
    $ent=cli_node($nom);
    $ctx=stream_context_create(['http'=>['method'=>$method,'timeout'=>8,'ignore_errors'=>true,
        'follow_location'=>0,'header'=>"Authorization: Bearer ".cli_ticket($tec,$nom,'control')."\r\nAccept: application/json\r\n"],
        'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);
    $txt=@file_get_contents($ent['url'].$path,false,$ctx);
    $status=$http_response_header[0]??'';
    if($txt===false||!preg_match('/^HTTP\/\S+ 2\d\d\b/',$status)) throw new RuntimeException('CLI no disponible o solicitud rechazada.');
    return json_decode($txt,true,32,JSON_THROW_ON_ERROR);
}
function totp_decode(string $txt): string {
    if(!preg_match('/^[A-Z2-7]{32}$/',$txt))throw new InvalidArgumentException('Semilla TOTP inválida.');
    $bits='';foreach(str_split($txt) as $chr)$bits.=str_pad(decbin(strpos('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567',$chr)),5,'0',STR_PAD_LEFT);
    $raw='';foreach(str_split($bits,8) as $byte)$raw.=chr(bindec($byte));return $raw;
}
function totp_code(string $seed,int $step): string {
    $mac=hash_hmac('sha1',pack('N2',intdiv($step,4294967296),$step%4294967296),totp_decode($seed),true);
    $off=ord($mac[19])&15;$num=unpack('N',substr($mac,$off,4))[1]&0x7fffffff;
    return str_pad((string)($num%1000000),6,'0',STR_PAD_LEFT);
}
function totp_paso(string $seed,string $code,int $anterior=-1): int {
    if(!preg_match('/^\d{6}$/',$code))throw new InvalidArgumentException('Código TOTP de seis cifras requerido.');
    $step=intdiv(time(),30);
    foreach([$step-1,$step,$step+1] as $val)
        if($val>$anterior&&hash_equals(totp_code($seed,$val),$code))return $val;
    throw new InvalidArgumentException('Código TOTP incorrecto, caducado o ya utilizado.');
}
function totp_inicia(array $tec,string $pwd): void {
    limita('totp_alta');
    $act=cli_auth();$usr=usuario_actual();
    if($act['id']!==$tec['id']||isset($act['totp_seed']))
        throw new InvalidArgumentException('Segundo factor ya configurado o perfil no disponible.');
    if(!$usr||login_usuario($usr['correo'],$pwd)!==$usr['id'])
        throw new InvalidArgumentException('Contraseña de la cuenta incorrecta.');
    $seed='';for($num=0;$num<32;$num++)$seed.='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'[random_int(0,31)];
    // Enrollment stays in the authenticated session until possession is proved.
    $_SESSION['totp_alta']=['id'=>$tec['id'],'usuario'=>$usr['id'],'seed'=>$seed,'creado'=>time()];
}
function totp_confirma(array $tec,string $code): void {
    limita('totp');$act=cli_auth();$usr=usuario_actual();$alta=$_SESSION['totp_alta']??[];
    if(!$usr||$act['id']!==$tec['id']||isset($act['totp_seed'])||
       ($alta['id']??'')!==$tec['id']||($alta['usuario']??'')!==$usr['id']||
       time()-($alta['creado']??0)>300)
        throw new InvalidArgumentException('Configuración caducada o ya completada. Iniciar de nuevo.');
    $step=totp_paso($alta['seed'],$code);
    datos(function(&$dat)use($tec,$alta,$step){
        foreach($dat['tecnicos'] as &$ent)if($ent['id']===$tec['id']){
            if($ent['estado']!=='activo'||isset($ent['totp_seed']))
                throw new InvalidArgumentException('El perfil cambió durante la configuración.');
            $ent['totp_seed']=$alta['seed'];$ent['totp_step']=$step;return;
        }throw new InvalidArgumentException('Perfil no disponible.');
    },true);
    $_SESSION['cli_2fa']=time();$_SESSION['cli_2fa_tec']=$tec['id'];
    $_SESSION['cli_2fa_seed']=hash('sha256',$alta['seed']);unset($_SESSION['totp_alta']);
}
function cli_totp(array $tec,string $code): void {
    if(!preg_match('/^\d{6}$/',$code))throw new InvalidArgumentException('Código TOTP de seis cifras requerido.');
    limita('totp');
    datos(function(&$dat)use($tec,$code){
        foreach($dat['tecnicos'] as &$ent)if($ent['id']===$tec['id']){
            if(!isset($ent['totp_seed']))throw new InvalidArgumentException('Activar TOTP con administración antes de usar la terminal.');
            $ent['totp_step']=totp_paso($ent['totp_seed'],$code,$ent['totp_step']??-1);return;
        }throw new InvalidArgumentException('Perfil no disponible.');
    },true);
    $_SESSION['cli_2fa']=time();$_SESSION['cli_2fa_tec']=$tec['id'];
    $_SESSION['cli_2fa_seed']=hash('sha256',$tec['totp_seed']);
}
function cli_auth(): array {
    $usr=usuario_actual();$tec=$usr?perfil_usuario($usr):null;
    if(!$usr||!$tec||$tec['estado']!=='activo'||!($tec['email_confirmado']??false))throw new InvalidArgumentException('Se requiere un técnico activo y confirmado.');
    return $tec;
}
function cli_lease(array $tec): void {
    if(($_SESSION['cli_2fa_tec']??'')!==$tec['id']||time()-($_SESSION['cli_2fa']??0)>900||
        !isset($tec['totp_seed'])||!hash_equals(hash('sha256',$tec['totp_seed']),$_SESSION['cli_2fa_seed']??''))
        throw new InvalidArgumentException('Confirmar el segundo factor para abrir o mantener la terminal.');
}
