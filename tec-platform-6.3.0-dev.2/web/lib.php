<?php
/** Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
 * Author & Credits: https://www.alawise.es/1-s
 * Shared JSON store; every reader and writer uses the same advisory lock.
 */
declare(strict_types=1);
if (!defined('AUX_ASSIST_ENTRY')) { http_response_code(404); exit; }
const ASIST_VERSION = '6.3.0-dev.2';
function pth_datos(): string {
    $pth = config_tec('data_dir','AUX_ASSIST_DATA_DIR','/var/lib/aux-assist');
    if ($pth[0] !== '/') throw new RuntimeException('Data directory must be absolute.');
    return rtrim($pth, '/');
}
function esc(string $txt): string { return htmlspecialchars($txt, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function fecha(): string { return gmdate('Y-m-d\TH:i:s\Z'); }
function lee_json(string $pth): array {
    if (!is_file($pth)) return [];
    $dat = json_decode((string)file_get_contents($pth), true, 64, JSON_THROW_ON_ERROR);
    if (!is_array($dat) || !array_is_list($dat)) throw new RuntimeException('Invalid JSON inventory.');
    return $dat;
}
function esc_json(string $pth, array $dat): void {
    // Rename replaces the complete file while the separate lock remains held.
    $tmp = tempnam(dirname($pth), '.aux-');
    if ($tmp === false) throw new RuntimeException('Cannot create temporary JSON.');
    try {
        chmod($tmp, 0600);
        $txt = json_encode(array_values($dat), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR) . "\n";
        if (file_put_contents($tmp, $txt) !== strlen($txt)) throw new RuntimeException('Incomplete JSON write.');
        $fd = fopen($tmp, 'r+');
        if ($fd === false || !fflush($fd) || (function_exists('fsync') && !fsync($fd))) throw new RuntimeException('Cannot flush JSON.');
        fclose($fd);
        if (!rename($tmp, $pth)) throw new RuntimeException('Cannot replace JSON.');
    } finally { if (is_file($tmp)) unlink($tmp); }
}
function datos(callable $fn, bool $escribe = false) {
    $pth = pth_datos();
    if (!is_dir($pth) && !mkdir($pth, 0700, true) && !is_dir($pth)) throw new RuntimeException('Cannot create data directory.');
    $fd = fopen($pth . '/.store.lock', 'c+');
    if ($fd === false || !flock($fd, $escribe ? LOCK_EX : LOCK_SH)) throw new RuntimeException('Cannot lock data.');
    chmod($pth . '/.store.lock', 0600);
    try {
        $dat = ['usuarios' => lee_json($pth . '/usuarios.json'), 'tecnicos' => lee_json($pth . '/tecnicos.json'), 'solicitudes' => lee_json($pth . '/solicitudes.json')];
        $res = $fn($dat);
        if ($escribe) {
            // Operations modify one inventory at a time; there is no two-file transaction claim.
            foreach ($dat as $nom => $val) {
                $arc = $pth . '/' . $nom . '.json';
                if (lee_json($arc) !== $val) esc_json($arc, $val);
            }
        }
        return $res;
    } finally { flock($fd, LOCK_UN); fclose($fd); }
}
function campo(array $dat, string $nom, int $max, bool $oblig = true): string {
    if (!isset($dat[$nom]) || !is_string($dat[$nom])) {
        if (!$oblig) return '';
        throw new InvalidArgumentException('Falta el campo ' . $nom . '.');
    }
    $txt = trim($dat[$nom]);
    if (($oblig && $txt === '') || strlen($txt) > $max || preg_match('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', $txt) || (!in_array($nom,['mensaje','biografia'],true) && preg_match('/[\r\n\t]/', $txt)))
        throw new InvalidArgumentException('Campo inválido: ' . $nom . '.');
    return $txt;
}
function correo(string $txt): string {
    $txt = strtolower(trim($txt));
    if (strlen($txt) > 254 || !filter_var($txt, FILTER_VALIDATE_EMAIL)) throw new InvalidArgumentException('Correo inválido.');
    return $txt;
}
function telefono(string $txt): string {
    $txt = trim($txt);
    $n = preg_match_all('/[0-9]/', $txt);
    if (strlen($txt) > 32 || !preg_match('/^\+?[0-9][0-9(). -]{5,24}$/', $txt) || $n < 7 || $n > 15)
        throw new InvalidArgumentException('Teléfono inválido; usar formato internacional si es posible.');
    return $txt;
}
function enlace_confirmacion(string $tipo, string $id, string $token): string {
    $base = rtrim(config_tec('public_url','AUX_ASSIST_PUBLIC_URL','https://tec.1-s.es'), '/');
    return $base . '/index.php?confirm=' . rawurlencode($tipo) . '&id=' . rawurlencode($id) . '&token=' . rawurlencode($token);
}
function correo_remitente(): string {
    $from = config_tec('mail_from','AUX_ASSIST_MAIL_FROM','tec@1wise.es');
    if ($from === '') throw new RuntimeException('AUX_ASSIST_MAIL_FROM is not configured.');
    try { return correo($from); }
    catch (InvalidArgumentException $exc) { throw new RuntimeException('AUX_ASSIST_MAIL_FROM is invalid.', 0, $exc); }
}
function envia_confirmacion(string $tipo, string $id, string $mail, string $token): void {
    $nombres = ['tecnico'=>'alta de técnico','cliente'=>'solicitud de asistencia','usuario'=>'registro de usuario'];
    if (!isset($nombres[$tipo])) throw new InvalidArgumentException('Tipo de confirmación inválido.');
    $from = correo_remitente();
    $url = enlace_confirmacion($tipo, $id, $token);
    $asunto = 'Confirma tu correo · TEC';
    $cuerpo = "Se ha solicitado " . $nombres[$tipo] . ".\n\n" .
        "Abre este enlace para confirmar el correo (válido durante 24 horas):\n" . $url . "\n\n" .
        "Si no hiciste esta solicitud, ignora este mensaje.\n";
    $cab = "From: TEC <{$from}>\r\n" . "Content-Type: text/plain; charset=UTF-8\r\n" . "MIME-Version: 1.0";
    $asunto = '=?UTF-8?B?' . base64_encode($asunto) . '?=';
    if (!mail($mail, $asunto, $cuerpo, $cab)) throw new RuntimeException('No se pudo entregar el correo de confirmación. Revisar el MTA local.');
}
function crea_confirmacion(): array {
    $token = bin2hex(random_bytes(32));
    return [$token, hash('sha256', $token), time() + 86400];
}
function confirma_email(string $tipo, string $id, string $token): void {
    if (!in_array($tipo, ['tecnico','cliente','usuario'], true) || !preg_match('/^[a-f0-9]{64}$/', $token))
        throw new InvalidArgumentException('Enlace de confirmación inválido.');
    datos(function (&$dat) use ($tipo,$id,$token) {
        $col = $tipo === 'usuario' ? 'usuarios' : ($tipo === 'tecnico' ? 'tecnicos' : 'solicitudes');
        foreach ($dat[$col] as &$ent) if ($ent['id'] === $id) {
            if ($ent['estado'] !== ($tipo !== 'cliente' ? 'verificacion_pendiente' : 'confirmacion_pendiente'))
                throw new InvalidArgumentException('El registro no permite esta confirmación.');
            if (($ent['email_confirmado'] ?? false) === true) throw new InvalidArgumentException('Este correo ya está confirmado.');
            if (($ent['confirm_expira'] ?? 0) <= time() || !hash_equals((string)($ent['confirm_hash'] ?? ''), hash('sha256', $token)))
                throw new InvalidArgumentException('El enlace es inválido o ha caducado. Solicitar un nuevo correo de confirmación.');
            $ent['email_confirmado'] = true;
            $ent['estado'] = $tipo === 'usuario' ? 'activo' : 'pendiente';
                if($tipo==='tecnico' && isset($ent['usuario_id'])) {
                foreach($dat['usuarios'] as &$usr) if($usr['id']===$ent['usuario_id']) {
                    $usr['email_confirmado']=true;$usr['estado']='activo';unset($usr['confirm_hash'],$usr['confirm_expira']);
                } unset($usr);
            }
            $ent['actualizado'] = fecha();
            unset($ent['confirm_hash'], $ent['confirm_expira']);
            return;
        }
        throw new InvalidArgumentException('Registro no encontrado.');
    }, true);
}
function valida_confirmacion(string $tipo, string $id, string $token): void {
    if (!in_array($tipo, ['tecnico','cliente','usuario'], true) || !preg_match('/^[a-f0-9]{64}$/', $token))
        throw new InvalidArgumentException('Enlace de confirmación inválido.');
    $ok = datos(function ($dat) use ($tipo,$id,$token) {
        $col = $tipo === 'usuario' ? 'usuarios' : ($tipo === 'tecnico' ? 'tecnicos' : 'solicitudes');
        foreach ($dat[$col] as $ent) if ($ent['id'] === $id)
            return $ent['estado'] === ($tipo !== 'cliente' ? 'verificacion_pendiente' : 'confirmacion_pendiente') && !($ent['email_confirmado'] ?? false) && ($ent['confirm_expira'] ?? 0) > time() &&
                hash_equals((string)($ent['confirm_hash'] ?? ''), hash('sha256', $token));
        return false;
    });
    if (!$ok) throw new InvalidArgumentException('El enlace es inválido o ha caducado.');
}
function reenvia_confirmacion(string $id): void {
    $tipo = str_starts_with($id, 'usr_') ? 'usuario' : (str_starts_with($id, 'tec_') ? 'tecnico' : (str_starts_with($id, 'sol_') ? 'cliente' : ''));
    if ($tipo === '') throw new InvalidArgumentException('Identificador inválido.');
    [$token,$token_hash,$expira] = crea_confirmacion();
    $mail = datos(function (&$dat) use ($tipo,$id,$token_hash,$expira) {
        $col = $tipo === 'usuario' ? 'usuarios' : ($tipo === 'tecnico' ? 'tecnicos' : 'solicitudes');
        foreach ($dat[$col] as &$ent) if ($ent['id'] === $id) {
            if (($ent['email_confirmado'] ?? false) || !in_array($ent['estado'], ['verificacion_pendiente','confirmacion_pendiente'], true))
                throw new InvalidArgumentException('El registro no espera confirmación de correo.');
            $ent['confirm_hash']=$token_hash; $ent['confirm_expira']=$expira; $ent['actualizado']=fecha();
            return $tipo !== 'cliente' ? $ent['correo'] : $ent['cliente_correo'];
        }
        throw new InvalidArgumentException('Registro no encontrado.');
    }, true);
    envia_confirmacion($tipo,$id,$mail,$token);
}
function clave_publica(string $txt): string {
    $txt = trim($txt);
    if (str_contains($txt, "\n") || str_contains($txt, "\r")) throw new InvalidArgumentException('Se requiere una única clave pública.');
    $par = preg_split('/\s+/', $txt, 3);
    if (count($par) < 2 || !in_array($par[0], ['ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521'], true))
        throw new InvalidArgumentException('Formato de clave pública no admitido.');
    $byt = base64_decode($par[1], true);
    if ($byt === false || strlen($byt) < 8 || strlen($byt) > 8192) throw new InvalidArgumentException('Clave pública inválida.');
    $tam = unpack('N', substr($byt, 0, 4))[1];
    if ($tam > strlen($byt) - 4 || substr($byt, 4, $tam) !== $par[0]) throw new InvalidArgumentException('Tipo de clave incompatible.');
    // OpenSSH validates the entire key, including curve/length, without a shell or temp file.
    $pro = proc_open(['/usr/bin/ssh-keygen', '-l', '-f', '/dev/stdin'], [['pipe','r'],['pipe','w'],['pipe','w']], $pipes);
    if (!is_resource($pro)) throw new RuntimeException('OpenSSH key validation unavailable.');
    fwrite($pipes[0], $par[0] . ' ' . $par[1] . "\n"); fclose($pipes[0]);
    stream_get_contents($pipes[1]); fclose($pipes[1]); stream_get_contents($pipes[2]); fclose($pipes[2]);
    if (proc_close($pro) !== 0) throw new InvalidArgumentException('OpenSSH rechaza la clave pública.');
    return $par[0] . ' ' . $par[1];
}
function alta_tecnico(array $frm): string {
    $nom = campo($frm, 'nombre', 100); $mail = correo(campo($frm, 'correo', 254));
    $con = campo($frm, 'contacto', 200); $tel = telefono(campo($frm, 'telefono', 32)); $cla = clave_publica(campo($frm, 'clave', 12000));
    $pwd = campo($frm, 'password', 72);
    if (strlen($pwd) < 12) throw new InvalidArgumentException('La contraseña requiere de 12 a 72 bytes.');
    if (($frm['publicar'] ?? '') !== 'si') throw new InvalidArgumentException('Se requiere aceptar la publicación del nombre, contacto, teléfono y clave pública.');
    correo_remitente();
    $hash = password_hash($pwd, PASSWORD_DEFAULT); [$token,$token_hash,$expira] = crea_confirmacion();
    $id = datos(function (&$dat) use ($nom,$mail,$con,$tel,$cla,$hash,$token_hash,$expira) {
        foreach (array_merge($dat['usuarios'],$dat['tecnicos']) as $ent) if ($ent['correo'] === $mail) throw new InvalidArgumentException('Alta no disponible; revisar la cuenta con administración.');
        $id = 'tec_' . bin2hex(random_bytes(12));
        $dat['tecnicos'][] = ['id'=>$id,'nombre'=>$nom,'correo'=>$mail,'telefono'=>$tel,'contacto'=>$con,'clave'=>$cla,
            'password_hash'=>$hash,'email_confirmado'=>false,'confirm_hash'=>$token_hash,'confirm_expira'=>$expira,
            'estado'=>'verificacion_pendiente','creado'=>fecha(),'actualizado'=>fecha()];
        return $id;
    }, true);
    envia_confirmacion('tecnico', $id, $mail, $token);
    return $id;
}
function publica(array $ent): array {
        $ent += ['url'=>'','empresa'=>'','biografia'=>''];
    return array_intersect_key($ent, array_flip(['id','nombre','contacto','correo','telefono','url','empresa','biografia','clave']));
}
function tecnicos_publicos(): array {
    return datos(fn($dat) => array_map('publica', array_values(array_filter($dat['tecnicos'], fn($t) => $t['estado'] === 'activo' && ($t['email_confirmado'] ?? false) && (!isset($t['usuario_id']) || usuario_por_id($dat,$t['usuario_id']) !== null)))));
}
function tecnico_actual(): ?array {
    $id = $_SESSION['tecnico'] ?? '';
    return datos(function ($dat) use ($id) { foreach ($dat['tecnicos'] as $ent) if ($ent['id'] === $id && $ent['estado'] === 'activo' && ($ent['email_confirmado'] ?? false)) return $ent; return null; });
}
function login_tecnico(string $mail, string $pwd): ?string {
    return datos(function ($dat) use ($mail,$pwd) {
        foreach ($dat['tecnicos'] as $ent) if ($ent['correo']===$mail && $ent['estado']==='activo' && ($ent['email_confirmado']??false)) {
            if(isset($ent['usuario_id'])) {
                foreach($dat['usuarios'] as $usr) if($usr['id']===$ent['usuario_id'] && $usr['estado']==='activo' && ($usr['email_confirmado']??false) && password_verify($pwd,$usr['password_hash'])) return $ent['id'];
            } elseif(isset($ent['password_hash']) && password_verify($pwd,$ent['password_hash'])) return $ent['id'];
        }
        return null;
    });
}
function alta_solicitud(array $frm): string {
    $tec_id = campo($frm, 'tecnico_id', 40); $mail = correo(campo($frm, 'cliente_correo', 254)); $tel = telefono(campo($frm, 'cliente_telefono', 32));
    $nom = campo($frm, 'cliente', 100); $msg = campo($frm, 'mensaje', 4000);
    correo_remitente();
    [$token,$token_hash,$expira] = crea_confirmacion();
    $id = datos(function (&$dat) use ($tec_id,$mail,$tel,$nom,$msg,$token_hash,$expira) {
        $activo = false;
        foreach ($dat['tecnicos'] as $tec) if ($tec['id'] === $tec_id && $tec['estado'] === 'activo' && ($tec['email_confirmado'] ?? false)) { $activo = true; break; }
        if (!$activo) throw new InvalidArgumentException('Técnico no disponible. Seleccionar un perfil activo.');
        $id = 'sol_' . bin2hex(random_bytes(12));
        $dat['solicitudes'][] = ['id'=>$id,'tecnico_id'=>$tec_id,'cliente_correo'=>$mail,'cliente_telefono'=>$tel,'cliente'=>$nom,'mensaje'=>$msg,
            'email_confirmado'=>false,'confirm_hash'=>$token_hash,'confirm_expira'=>$expira,
            'estado'=>'confirmacion_pendiente','creado'=>fecha(),'actualizado'=>fecha()];
        return $id;
    }, true);
    envia_confirmacion('cliente', $id, $mail, $token);
    return $id;
}
function solicitudes_tecnico(array $tec): array {
    return datos(fn($dat)=>array_values(array_filter($dat['solicitudes'],fn($ent)=>
        $ent['tecnico_id'] === $tec['id'] && ($ent['email_confirmado'] ?? false))));
}
function cambia_solicitud(string $id, array $tec, string $estado): void {
    if (!in_array($estado, ['aceptada','rechazada','cerrada'], true)) throw new InvalidArgumentException('Estado no admitido.');
    datos(function (&$dat) use ($id,$tec,$estado) {
        foreach ($dat['solicitudes'] as &$ent) if ($ent['id'] === $id && $ent['tecnico_id'] === $tec['id'] && ($ent['email_confirmado'] ?? false)) {
            $validos = ['pendiente'=>['aceptada','rechazada'],'aceptada'=>['cerrada']];
            if (!in_array($estado, $validos[$ent['estado']] ?? [], true)) throw new InvalidArgumentException('Transición no permitida.');
            $ent['estado']=$estado; $ent['actualizado']=fecha(); return;
        }
        throw new InvalidArgumentException('Solicitud no disponible.');
    }, true);
}
function limita(string $accion): void {
    // Per-address quotas survive PHP worker changes and never store raw IP addresses.
    $pth = pth_datos(); if (!is_dir($pth)) datos(fn($dat)=>null);
    $fd = fopen($pth . '/.limits.lock','c+');
    if ($fd === false || !flock($fd, LOCK_EX)) throw new RuntimeException('Cannot lock rate limits.');
    chmod($pth . '/.limits.lock',0600);
    try {
        $arc = $pth . '/limites.json'; $dat = lee_json($arc); $tms = time();
        $dat = array_values(array_filter($dat, fn($ent)=>$ent['hasta'] > $tms));
        $id = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? 'cli') . ':' . $accion);
        $max = ['alta'=>5,'login'=>15,'solicitud'=>10,'contacto'=>5,'aplicar'=>5][$accion] ?? 30;
        foreach ($dat as &$ent) if ($ent['id'] === $id) {
            if ($ent['cantidad'] >= $max) throw new InvalidArgumentException('Límite temporal alcanzado. Volver a intentar más tarde.');
            $ent['cantidad']++; esc_json($arc,$dat); return;
        }
        unset($ent); $dat[]=['id'=>$id,'cantidad'=>1,'hasta'=>$tms+900]; esc_json($arc,$dat);
    } finally { flock($fd, LOCK_UN); fclose($fd); }
}

function config_proyecto(): array {
    static $cfg = null;
    if ($cfg !== null) return $cfg;
    $pth = getenv('AUX_ASSIST_CONFIG') ?: '/var/www/aux.1-s.es/fast-boot.json';
    if (!is_file($pth)) return $cfg = [];
    $cfg = json_decode((string)file_get_contents($pth), true, 32, JSON_THROW_ON_ERROR);
    if (!is_array($cfg)) throw new RuntimeException('Invalid project configuration.');
    return $cfg;
}
function config_tec(string $nom, string $env, string $def): string {
    $val = $env !== '' ? getenv($env) : false;
    if ($val !== false && $val !== '') return $val;
    $cfg = config_proyecto()['tec'] ?? [];
    return isset($cfg[$nom]) && is_string($cfg[$nom]) ? $cfg[$nom] : $def;
}
function url_publica(string $url): string {
    if ($url === '') return '';
    $part = parse_url($url);
    if (!filter_var($url, FILTER_VALIDATE_URL) || !in_array($part['scheme'] ?? '', ['https','http'],true) || isset($part['user']) || isset($part['pass']))
        throw new InvalidArgumentException('URL pública inválida; usar http o https sin credenciales.');
    return $url;
}
function alta_usuario(array $frm): string {
    $nom=campo($frm,'nombre',100); $mail=correo(campo($frm,'correo',254)); $tel=telefono(campo($frm,'telefono',32));
    $pwd=campo($frm,'password',72);
    if(strlen($pwd)<12) throw new InvalidArgumentException('La contraseña requiere de 12 a 72 bytes.');
    correo_remitente(); [$token,$hash_token,$expira]=crea_confirmacion(); $hash_pwd=password_hash($pwd,PASSWORD_DEFAULT);
    $id=datos(function(&$dat)use($nom,$mail,$tel,$hash_pwd,$hash_token,$expira){
        foreach(array_merge($dat['usuarios'],$dat['tecnicos']) as $ent) if($ent['correo']===$mail)
            throw new InvalidArgumentException('Registro no disponible; usar la cuenta existente o contactar con administración.');
        $id='usr_'.bin2hex(random_bytes(12));
        $dat['usuarios'][]=['id'=>$id,'nombre'=>$nom,'correo'=>$mail,'telefono'=>$tel,'password_hash'=>$hash_pwd,
            'email_confirmado'=>false,'confirm_hash'=>$hash_token,'confirm_expira'=>$expira,'estado'=>'verificacion_pendiente','creado'=>fecha(),'actualizado'=>fecha()];
        return $id;
    },true);
    envia_confirmacion('usuario',$id,$mail,$token); return $id;
}
function usuario_por_id(array $dat,string $id): ?array {
    foreach($dat['usuarios'] as $ent) if($ent['id']===$id && $ent['estado']==='activo' && ($ent['email_confirmado']??false)) return $ent;
    // Legacy confirmed technicians can keep signing in until the CLI migration is run.
    foreach($dat['tecnicos'] as $ent) if($ent['id']===$id && $ent['estado']==='activo' && ($ent['email_confirmado']??false)) {
        if(isset($ent['usuario_id'])) return usuario_por_id($dat,$ent['usuario_id']);
        return ['id'=>$ent['id'],'nombre'=>$ent['nombre'],'correo'=>$ent['correo'],'telefono'=>$ent['telefono'],'email_confirmado'=>true,'estado'=>'activo'];
    }
    return null;
}
function usuario_actual(): ?array {
    return datos(fn($dat)=>usuario_por_id($dat,$_SESSION['usuario']??$_SESSION['tecnico']??''));
}
function login_usuario(string $mail,string $pwd): ?string {
    return datos(function($dat)use($mail,$pwd){
        foreach($dat['usuarios'] as $ent) if($ent['correo']===$mail) {
            return $ent['estado']==='activo' && ($ent['email_confirmado']??false) && password_verify($pwd,$ent['password_hash']) ? $ent['id'] : null;
        }
        foreach($dat['tecnicos'] as $ent) if($ent['correo']===$mail && isset($ent['password_hash']) && $ent['estado']==='activo' && ($ent['email_confirmado']??false) && password_verify($pwd,$ent['password_hash'])) return $ent['id'];
        return null;
    });
}
function perfil_usuario(array $usr): ?array {
    return datos(function($dat)use($usr){
        foreach($dat['tecnicos'] as $ent) if(($ent['usuario_id']??$ent['id'])===$usr['id']) return $ent;
        return null;
    });
}
function aplica_tecnico(array $usr,array $frm): string {
    $url=url_publica(campo($frm,'url',500)); $emp=campo($frm,'empresa',150); $bio=campo($frm,'biografia',4000);
    $cla=clave_publica(campo($frm,'clave',12000));
    if(($frm['publicar']??'')!=='si') throw new InvalidArgumentException('Aceptar la publicación del correo, teléfono, URL, empresa, biografía y clave pública.');
    return datos(function(&$dat)use($usr,$url,$emp,$bio,$cla){
        $act=usuario_por_id($dat,$usr['id']); if(!$act) throw new InvalidArgumentException('Cuenta no disponible.');
        foreach($dat['tecnicos'] as &$ent) if(($ent['usuario_id']??$ent['id'])===$act['id']) {
            if($ent['estado']==='suspendido') throw new InvalidArgumentException('El perfil está suspendido; contactar con administración.');
            // Public profile changes require the same review as a new application.
            $ent=array_merge($ent,['nombre'=>$act['nombre'],'correo'=>$act['correo'],'telefono'=>$act['telefono'],'contacto'=>$url,'url'=>$url,'empresa'=>$emp,'biografia'=>$bio,'clave'=>$cla,'email_confirmado'=>true,'estado'=>'pendiente','actualizado'=>fecha()]);
            return $ent['id'];
        }
        unset($ent); $id='tec_'.bin2hex(random_bytes(12));
        $dat['tecnicos'][]=['id'=>$id,'usuario_id'=>$act['id'],'nombre'=>$act['nombre'],'correo'=>$act['correo'],'telefono'=>$act['telefono'],'contacto'=>$url,'url'=>$url,'empresa'=>$emp,'biografia'=>$bio,'clave'=>$cla,'email_confirmado'=>true,'estado'=>'pendiente','creado'=>fecha(),'actualizado'=>fecha()];
        return $id;
    },true);
}
function solicita_usuario(array $usr,array $frm): string {
    $tec_id=campo($frm,'tecnico_id',40); $msg=campo($frm,'mensaje',4000);
    return datos(function(&$dat)use($usr,$tec_id,$msg){
        $act=usuario_por_id($dat,$usr['id']); if(!$act) throw new InvalidArgumentException('Cuenta no disponible.');
        $tec=null;foreach($dat['tecnicos'] as $ent) if($ent['id']===$tec_id && $ent['estado']==='activo' && ($ent['email_confirmado']??false)) $tec=$ent;
        if(!$tec || isset($tec['usuario_id']) && !usuario_por_id($dat,$tec['usuario_id'])) throw new InvalidArgumentException('Técnico no disponible.');
        if(($tec['usuario_id']??$tec['id'])===$act['id']) throw new InvalidArgumentException('Elegir otro técnico para pedir asistencia.');
        $id='sol_'.bin2hex(random_bytes(12));
        $dat['solicitudes'][]=['id'=>$id,'usuario_id'=>$act['id'],'tecnico_id'=>$tec_id,'cliente'=>$act['nombre'],'cliente_correo'=>$act['correo'],'cliente_telefono'=>$act['telefono'],'mensaje'=>$msg,'email_confirmado'=>true,'estado'=>'pendiente','creado'=>fecha(),'actualizado'=>fecha()];
        return $id;
    },true);
}
function solicitudes_usuario(array $usr): array {
    return datos(fn($dat)=>array_values(array_filter($dat['solicitudes'],fn($s)=>($s['usuario_id']??'')===$usr['id'])));
}
function contacto_administrador(array $usr,array $frm): void {
    $msg=campo($frm,'mensaje',4000);
    $act=datos(fn($dat)=>usuario_por_id($dat,$usr['id'])); if(!$act) throw new InvalidArgumentException('Cuenta no disponible.');
    $to=correo(config_tec('admin_mail','AUX_ASSIST_ADMIN_MAIL','tec@1wise.es'));
    $from=correo_remitente(); $reply=correo($act['correo']);
    $cab=['From'=>'TEC <'.$from.'>','Reply-To'=>$reply,'Content-Type'=>'text/plain; charset=UTF-8','MIME-Version'=>'1.0'];
    $body='Usuario: '.$act['nombre']."\nCorreo: ".$reply."\nTeléfono: ".$act['telefono']."\nID: ".$act['id']."\n\n".$msg."\n";
    if(!mail($to,'=?UTF-8?B?'.base64_encode('Contacto de usuario · TEC').'?=',$body,$cab)) throw new RuntimeException('El MTA no aceptó el correo de contacto.');
}
function migra_usuarios(): int {
    return datos(function(&$dat){
        $n=0;
        foreach($dat['tecnicos'] as &$tec) {
            if(isset($tec['usuario_id'])) continue;
            $usr=null;foreach($dat['usuarios'] as $ent) if($ent['correo']===$tec['correo']) $usr=$ent;
            if($usr && !($usr['email_confirmado']??false) && $usr['id']!=='usr_'.substr(hash('sha256',$tec['id']),0,24)) throw new InvalidArgumentException('Existe un usuario sin confirmar con ese correo; resolver antes de migrar.');
            if(!$usr) {
                if(!isset($tec['password_hash'])) throw new InvalidArgumentException('Legacy account has no password hash.');
                $usr=['id'=>'usr_'.substr(hash('sha256',$tec['id']),0,24),'nombre'=>$tec['nombre'],'correo'=>$tec['correo'],'telefono'=>$tec['telefono'],'password_hash'=>$tec['password_hash'],
                    'email_confirmado'=>$tec['email_confirmado']??false,'estado'=>($tec['email_confirmado']??false)?'activo':'verificacion_pendiente','creado'=>$tec['creado'],'actualizado'=>fecha()];
                if(isset($tec['confirm_hash'])){$usr['confirm_hash']=$tec['confirm_hash'];$usr['confirm_expira']=$tec['confirm_expira'];}
                $dat['usuarios'][]=$usr;
            }
            $tec['usuario_id']=$usr['id']; $tec['url']??=filter_var($tec['contacto'],FILTER_VALIDATE_URL)?$tec['contacto']:'';
            $tec['empresa']??='';$tec['biografia']??=''; $n++;
        }
        return $n;
    },true);
}
