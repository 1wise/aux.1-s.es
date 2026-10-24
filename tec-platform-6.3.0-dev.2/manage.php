<?php
/** Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Approval is a local CLI operation, never an unauthenticated web endpoint.
 */
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
define('AUX_ASSIST_ENTRY',true); require __DIR__.'/web/lib.php';
require __DIR__.'/web/cli-lib.php';
try {
    $act=$argv[1]??'list'; $id=$argv[2]??'';
    if ($act==='init') { datos(function (&$dat) {return null;},true); foreach(['usuarios','tecnicos','solicitudes'] as $nom) if(!is_file(pth_datos().'/'.$nom.'.json')) esc_json(pth_datos().'/'.$nom.'.json',[]); echo "Initialized JSON store.\n"; }
    elseif ($act==='totp') {
        $seed='';for($num=0;$num<32;$num++)$seed.='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'[random_int(0,31)];
        datos(function(&$dat)use($id,$seed,$argv){foreach($dat['tecnicos'] as &$tec)if($tec['id']===$id){if(isset($tec['totp_seed'])&&!in_array('--replace',$argv,true))throw new InvalidArgumentException('TOTP already configured. Use --replace only to rotate the existing seed.');$tec['totp_seed']=$seed;$tec['totp_step']=-1;return;}throw new InvalidArgumentException('Technician not found.');},true);
        echo "Private TOTP enrollment seed (replaces previous seed): ".$seed."\n";
        echo 'otpauth://totp/AUX:'.rawurlencode($id).'?secret='.$seed.'&issuer=AUX&digits=6&period=30'."\n";
    }
    elseif ($act==='totp-reset') { datos(function(&$dat)use($id){foreach($dat['tecnicos'] as &$tec)if($tec['id']===$id){unset($tec['totp_seed'],$tec['totp_step']);return;}throw new InvalidArgumentException('Technician not found.');},true);echo "TOTP reset. Enroll again at totp.php.\n"; }
    elseif ($act==='migrate-users') { echo migra_usuarios()." migrated technician accounts.\n"; }
    elseif ($act==='users') datos(function($dat) { foreach($dat['usuarios'] as $ent) echo $ent['id']."\t".$ent['estado']."\t".$ent['correo']."\n"; });
    elseif ($act==='list') datos(function($dat) { foreach($dat['tecnicos'] as $ent) echo $ent['id']."\t".$ent['estado']."\t".$ent['correo']."\t".$ent['nombre']."\n"; });
    elseif(in_array($act,['suspend-user','activate-user'],true)) datos(function(&$dat)use($act,$id){
        foreach($dat['usuarios'] as &$usr)if($usr['id']===$id){
            if($act==='activate-user'&&!($usr['email_confirmado']??false))throw new InvalidArgumentException('Email must be confirmed.');
            $usr['estado']=$act==='suspend-user'?'suspendido':'activo';$usr['actualizado']=fecha();return;
        }throw new InvalidArgumentException('User not found.');
    },true);
    elseif ($act==='requests') datos(function($dat) { foreach($dat['solicitudes'] as $ent) echo $ent['id']."\t".$ent['estado']."\t".$ent['tecnico_id']."\t".$ent['cliente']."\n"; });
    elseif (in_array($act,['approve','suspend'],true)) datos(function (&$dat) use($act,$id) {
        foreach($dat['tecnicos'] as &$ent) if($ent['id']===$id) {
            if($act==='approve' && !($ent['email_confirmado'] ?? false)) throw new InvalidArgumentException('Technician email must be confirmed before approval.');
            $ent['estado']=$act==='approve'?'activo':'suspendido';$ent['actualizado']=fecha();echo $id.' '.$ent['estado']."\n";return;
        }
        throw new InvalidArgumentException('Technician not found.');
    },true);
    elseif ($act==='resend') { reenvia_confirmacion($id); echo "Confirmation email sent.\n"; }
    elseif ($act==='password') {
        // Read passwords from hidden terminal input or stdin, never process arguments.
        $tty=function_exists('stream_isatty')&&stream_isatty(STDIN);
        if($tty){fwrite(STDERR,"New password: ");exec('stty -echo');}
        try{$pwd=rtrim((string)fgets(STDIN),"\r\n");}finally{if($tty){exec('stty echo');fwrite(STDERR,"\n");}}
        if(strlen($pwd)<12||strlen($pwd)>72)throw new InvalidArgumentException('Password length must be 12 to 72 bytes.');
        $hash=password_hash($pwd,PASSWORD_DEFAULT);
        datos(function(&$dat)use($id,$hash){$usr_id=$id;foreach($dat['tecnicos'] as $ent)if($ent['id']===$id && isset($ent['usuario_id']))$usr_id=$ent['usuario_id'];foreach($dat['usuarios'] as &$usr)if($usr['id']===$usr_id){$usr['password_hash']=$hash;$usr['actualizado']=fecha();return;}unset($usr);foreach($dat['tecnicos'] as &$ent)if($ent['id']===$id){$ent['password_hash']=$hash;$ent['actualizado']=fecha();return;}throw new InvalidArgumentException('Account not found.');},true);
        echo "Password updated.\n";
    } else throw new InvalidArgumentException('Usage: php tec/manage.php init|users|migrate-users|list|requests|approve ID|suspend ID|resend ID|password ID|totp ID [--replace]|totp-reset ID');
} catch(Throwable $exc){fwrite(STDERR,$exc->getMessage()."\n");exit(1);}
