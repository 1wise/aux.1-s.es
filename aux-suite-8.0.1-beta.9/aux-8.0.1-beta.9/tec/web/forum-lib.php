<?php
/** Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
 * Author & Credits: https://www.alawise.es/1-s
 * Native TEC keeps public discussion separate from private assistance records.
 */
declare(strict_types=1);
if(!defined('AUX_ASSIST_ENTRY')){http_response_code(404);exit;}
const FORO_TABLEROS=['urls'=>'URL & Mirrors','deploy'=>'Deploy / 12 bits','pxe'=>'PXE Recipes'];
const FORO_TIPOS=['question'=>'Consulta','recipe'=>'Receta','bug'=>'Error','petition'=>'Petición','solution'=>'Solución'];
const FORO_EVIDENCIAS=['hypothesis'=>'Por comprobar','discovery'=>'Descubrimiento','simulated'=>'Simulada','tested'=>'Probada'];
const FORO_ESTADOS=['pending'=>'Pendiente de revisión','published'=>'Publicada','hidden'=>'Retirada'];
function foro_store(callable $fn,bool $res=false) {
    $pth=pth_datos();if(!is_dir($pth))datos(fn($d)=>null);
    $fd=fopen($pth.'/.forum.lock','c+');if(!$fd||!flock($fd,$res?LOCK_EX:LOCK_SH))throw new RuntimeException('Cannot lock forum.');
    chmod($pth.'/.forum.lock',0600);$arc=$pth.'/forum.json';
    try {
        $dat=['schema'=>1,'moderators'=>[],'topics'=>[],'replies'=>[],'reviews'=>[]];
        if(is_file($arc)) {
            if(filesize($arc)>67108864)throw new RuntimeException('Forum needs archival.');
            $dat=json_decode((string)file_get_contents($arc),true,64,JSON_THROW_ON_ERROR);
            if(($dat['schema']??null)!==1)throw new RuntimeException('Unsupported forum schema.');
            foreach(['moderators','topics','replies','reviews'] as $nom)if(!is_array($dat[$nom]??null))throw new RuntimeException('Invalid forum inventory.');
        }
        $result=$fn($dat);
        if($res) {
            $tmp=tempnam($pth,'.forum-');if(!$tmp)throw new RuntimeException('Cannot stage forum update.');
            try {
                chmod($tmp,0600);$txt=json_encode($dat,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR)."\n";
                if(file_put_contents($tmp,$txt)!==strlen($txt))throw new RuntimeException('Incomplete forum update.');
                $out=fopen($tmp,'r+');if(!$out||!fflush($out)||(function_exists('fsync')&&!fsync($out)))throw new RuntimeException('Cannot flush forum.');
                fclose($out);if(!rename($tmp,$arc))throw new RuntimeException('Cannot replace forum.');
            }finally{if(is_file($tmp))unlink($tmp);}
        }
        return $result;
    }finally{flock($fd,LOCK_UN);fclose($fd);}
}
function foro_field(array $frm,string $nom,int $max=160,bool $req=true):string {
    $txt=$frm[$nom]??'';
    if(!is_string($txt)||!preg_match('//u',$txt))throw new InvalidArgumentException('Revisar '.$nom.'.');
    $txt=trim($txt);
    if(($req&&$txt==='')||strlen($txt)>$max||preg_match('/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/',$txt))throw new InvalidArgumentException('Revisar '.$nom.'.');
    return $txt;
}
function foro_usuario(?array $usr):array {
    $act=$usr?datos(fn($d)=>usuario_por_id($d,$usr['id']??'')):null;
    if(!$act)throw new InvalidArgumentException('Entrar con una cuenta TEC confirmada.');
    return $act;
}
function foro_moderador(array $dat,?array $usr):bool{return $usr&&in_array($usr['id'],$dat['moderators'],true);}
function foro_visible(array $dat,array $ent,?array $usr):bool {
    return $ent['status']==='published'||($usr&&$ent['author']===$usr['id'])||foro_moderador($dat,$usr);
}
function foro_rol(string $id,bool $habilita):void {
    $usr=datos(fn($d)=>usuario_por_id($d,$id));if(!$usr)throw new InvalidArgumentException('Confirmed account not found.');
    foro_store(function(&$dat)use($usr,$habilita){$dat['moderators']=array_values(array_diff($dat['moderators'],[$usr['id']]));if($habilita)$dat['moderators'][]=$usr['id'];},true);
}
function foro_action(?array $usr,string $act,array $frm):string {
    $usr=foro_usuario($usr);
    return foro_store(function(&$dat)use($usr,$act,$frm){
        $now=time();$cnt=0;
        foreach(array_merge(array_values($dat['topics']),array_values($dat['replies'])) as $ent)if($ent['author']===$usr['id']&&$ent['created']>$now-600)$cnt++;
        if($cnt>=30)throw new InvalidArgumentException('Esperar unos minutos antes de aportar de nuevo.');
        if($act==='topic') {
            $ent=[];foreach(['title'=>160,'category'=>20,'evidence'=>20,'system'=>80,'release'=>80,'architecture'=>40,'firmware'=>60,'body'=>12000,'commands'=>12000,'proof'=>6000,'sources'=>2000,'name'=>80] as $nom=>$max)$ent[$nom]=foro_field($frm,$nom,$max,in_array($nom,['title','category','evidence','body','name'],true));
            if(!isset(FORO_TIPOS[$ent['category']],FORO_EVIDENCIAS[$ent['evidence']]))throw new InvalidArgumentException('Tipo o evidencia inválidos.');
            if(in_array($ent['category'],['recipe','solution'],true)&&$ent['commands']==='')throw new InvalidArgumentException('Indicar los comandos o pasos de la receta.');
            if(in_array($ent['evidence'],['tested','simulated'],true)&&strlen($ent['proof'])<20)throw new InvalidArgumentException('Describir el entorno y resultado de la prueba.');
            $refs=array_values(array_filter(array_map('trim',explode("\n",$ent['sources']))));
            if(count($refs)>10)throw new InvalidArgumentException('Usar hasta diez fuentes.');
            foreach($refs as $url){$p=parse_url($url);if(!$p||!filter_var($url,FILTER_VALIDATE_URL)||!in_array($p['scheme']??'',['http','https'],true)||isset($p['user'])||isset($p['pass']))throw new InvalidArgumentException('Fuentes: URL http/https sin credenciales.');}
            $ent['sources']=implode("\n",$refs);$ent['board']=foro_field($frm,'board',12,false)?:'pxe';if(!isset(FORO_TABLEROS[$ent['board']]))throw new InvalidArgumentException('Foro inválido.');$ent['policy12']=strtoupper(foro_field($frm,'policy12',3,false));if($ent['policy12']!==''&&($ent['board']!=='deploy'||!preg_match('/^[0-9A-F]{3}$/D',$ent['policy12'])))throw new InvalidArgumentException('Política 12 bits: usar tres hexadecimales en el foro Deploy.');$id='topic_'.bin2hex(random_bytes(12));$ent+=['id'=>$id,'slug'=>trim((string)preg_replace('/[^a-z0-9]+/','-',strtolower($ent['title'])),'-').'-'.substr($id,-8),'author'=>$usr['id'],'status'=>'pending','created'=>$now,'updated'=>$now];
            $dat['topics'][$id]=$ent;return $ent['slug'];
        }
        if($act==='reply') {
            $id=foro_field($frm,'topic',40);$ent=$dat['topics'][$id]??null;
            if(!$ent||!foro_visible($dat,$ent,$usr))throw new InvalidArgumentException('Tema no encontrado.');
            $rid='reply_'.bin2hex(random_bytes(12));$dat['replies'][$rid]=['id'=>$rid,'topic'=>$id,'author'=>$usr['id'],'name'=>foro_field($frm,'name',80),'body'=>foro_field($frm,'body',8000),'status'=>'pending','created'=>$now];return $ent['slug'];
        }
        if($act==='review') {
            if(!foro_moderador($dat,$usr))throw new InvalidArgumentException('Operación reservada a moderación.');
            $kind=foro_field($frm,'kind',10);$col=['topic'=>'topics','reply'=>'replies'][$kind]??'';$id=foro_field($frm,'id',40);$status=foro_field($frm,'status',20);
            if(!$col||!isset($dat[$col][$id],FORO_ESTADOS[$status]))throw new InvalidArgumentException('Revisión no válida.');
            $ent=$dat[$col][$id];$tema=$kind==='topic'?$ent:$dat['topics'][$ent['topic']];
            if($kind==='reply'&&$status==='published'&&$tema['status']!=='published')throw new InvalidArgumentException('Publicar primero el tema.');
            $note=foro_field($frm,'note',2000);$dat[$col][$id]['status']=$status;
            if($kind==='topic')$dat[$col][$id]['updated']=$now;
            $dat['reviews'][]=['target'=>$id,'kind'=>$kind,'action'=>$status,'note'=>$note,'author'=>$usr['id'],'name'=>$usr['nombre'],'created'=>$now];return $tema['slug'];
        }
        throw new InvalidArgumentException('Acción no admitida.');
    },true);
}


function foro_productos_datos():array {
    // Public generated products never touch private accounts or moderation data.
    $pth=__DIR__.'/products.aux.json';
    if(!is_file($pth)||filesize($pth)>2097152)return [];
    $dat=json_decode(file_get_contents($pth),true);
    return is_array($dat)?$dat:[];
}
function foro_productos(string $board):string {
    $dat=foro_productos_datos();if(!$dat)return '';
    $out='<section class="panel"><p class="eyebrow">PRODUCTOS PROPIOS AUX</p><h2>Recetas, políticas y orígenes para ampliar.</h2><p>Compromiso de revisión semanal. Última comprobación HTTP: '.esc($dat['updated_at']??'pendiente').'. HTTP accesible no equivale a arranque probado.</p><p><a href="https://aux.1-s.es/menu.ipxe">menu.ipxe</a> · <a href="https://aux.1-s.es/status.html">20 bits / JSON</a> · <a href="https://aux.1-s.es/urls.html">URL y mirrors</a></p>';
    if(in_array($board,['all','pxe'],true))foreach($dat['recipes']??[] as $rec){
        $out.='<article class="panel"><h3>'.esc($rec['title']).'</h3><p>'.esc($rec['release'].' · '.$rec['architecture'].' · '.$rec['method']).' · Login: pendiente</p><p>'.esc($rec['notes']).'</p><pre>'.esc($rec['commands']).'</pre><p><a href="'.esc($rec['procedure_url']?:$rec['original_url']).'">Procedimiento oficial</a> · <a href="'.esc(foro_url(['board'=>'pxe','new'=>'1','recipe'=>$rec['id']])).'">Ampliar esta receta</a></p></article>';
    }
    if(in_array($board,['all','deploy'],true))foreach($dat['policies']??[] as $rec)$out.='<p><code>'.esc($rec['policy']).'</code> · '.esc($rec['name']).' · '.esc($rec['description']).'</p>';
    if(in_array($board,['all','urls'],true)){$out.='<p>'.count($dat['urls']??[]).' referencias HTTP comprobadas; registro completo en URL y mirrors.</p>';foreach(array_slice($dat['urls']??[],0,10) as $rec)$out.='<p><a href="'.esc($rec['url']).'">'.esc($rec['name']).'</a> · '.esc($rec['checked_at']).'</p>';}
    return $out.'</section>';
}
