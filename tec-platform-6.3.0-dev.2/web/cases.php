<?php
/** Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
 * Author & Credits: https://www.alawise.es/1-s
 * Forms also work without JavaScript; polling updates connection badges in place.
 */
declare(strict_types=1);
define('AUX_ASSIST_ENTRY',true);
require __DIR__.'/lib.php';require __DIR__.'/cli-lib.php';require __DIR__.'/registry-lib.php';
if(($_SERVER['HTTPS']??'')!=='on') {http_response_code(403);exit('HTTPS required.');}
header('Cache-Control: no-store');header('Referrer-Policy: no-referrer');header('X-Content-Type-Options: nosniff');
header("Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
ini_set('session.use_strict_mode','1');ini_set('session.use_only_cookies','1');
session_name('tec_assist');session_set_cookie_params(['secure'=>true,'httponly'=>true,'samesite'=>'Lax','path'=>'/']);session_start();
$_SESSION['csrf']??=bin2hex(random_bytes(32));
$err='';$msg=$_SESSION['aviso']??'';unset($_SESSION['aviso']);$tec=null;$reg=null;$cas_sel=null;$clt_sel=null;$usb_sel=null;
try {
    $tec=cli_auth();
    if($_SERVER['REQUEST_METHOD']==='POST') {
        if((int)($_SERVER['CONTENT_LENGTH']??0)>16384||!is_string($_POST['csrf']??null)||!hash_equals($_SESSION['csrf'],$_POST['csrf']))
            throw new InvalidArgumentException('Expired form. Reload before submitting.');
        $act=reg_field($_POST,'action',24);
        if($act==='totp') {cli_totp($tec,reg_field($_POST,'code',6));header('Location: cases.php',true,303);exit;}
        cli_lease($tec);
        if($act==='sync') {
            // Release the PHP session lock while gateway requests are in flight.
            session_write_close();$res_sync=reg_sync($tec);$reg=reg_view($tec);
            if(($_POST['format']??'')==='json') {
                header('Content-Type: application/json');
                echo json_encode(['nodes'=>$res_sync,'cases'=>array_values(array_map(fn($ent)=>[
                    'id'=>$ent['id'],'code'=>$ent['code'],'title'=>$ent['title'],'connection'=>$ent['connection'],
                    'last_seen'=>$ent['last_seen'],'expires'=>$ent['expires']],$reg['cases']))],JSON_THROW_ON_ERROR);exit;
            }
            header('Location: cases.php',true,303);exit;
        }
        if($act==='import_requests') {
            $cnt_reg=reg_import_requests($tec);$_SESSION['aviso']=$cnt_reg.' clients imported from your confirmed assistance requests.';
            header('Location: cases.php#clients',true,303);exit;
        }
        if($act==='end_access') {
            $id=reg_field($_POST,'id',96);$ent=reg_store(fn($reg)=>reg_owned($reg,'cases',$id,$tec));
            if($ent['mode']!=='web') throw new InvalidArgumentException('A standalone direct session must be closed on its client.');
            cli_api($tec,$ent['node'],'/api/sessions/'.$ent['session_id'].'/close','POST');
            reg_sync($tec);$msg='SSH authorization closed. Case history is retained.';
        } else {
            $id=reg_action($tec,$act,$_POST);$msg='Register saved.';
        }
        $_SESSION['aviso']=$msg;
        $url='cases.php?'.http_build_query([in_array($act,['client_save','usb_save'],true)?($act==='client_save'?'client':'usb'):'case'=>$id]);
        header('Location: '.$url,true,303);exit;
    }
    cli_lease($tec);$reg=reg_view($tec);
    if(isset($_GET['case'])) $cas_sel=reg_owned($reg,'cases',reg_field($_GET,'case',96),$tec);
    if(isset($_GET['client'])) $clt_sel=reg_owned($reg,'clients',reg_field($_GET,'client',64),$tec);
    if(isset($_GET['usb'])) $usb_sel=reg_owned($reg,'usbs',reg_field($_GET,'usb',64),$tec);
} catch(Throwable $err) {
    $err=$err->getMessage();
    if($_SERVER['REQUEST_METHOD']==='POST'&&($_POST['format']??'')==='json') {
        http_response_code(403);header('Content-Type: application/json');echo json_encode(['error'=>$err]);exit;
    }
    // A rejected selector never falls back to displaying a different record.
    $reg=null;$cas_sel=$clt_sel=$usb_sel=null;
}
function reg_hidden(string $act,string $id=''): void {
    echo '<input type="hidden" name="csrf" value="'.esc($_SESSION['csrf']).'"><input type="hidden" name="action" value="'.esc($act).'"><input type="hidden" name="id" value="'.esc($id).'">';
}
function reg_input(string $nom,string $txt,string $val='',string $mode='text',int $max=120,bool $res=true): void {
    echo '<label>'.esc($txt).'<input name="'.esc($nom).'" type="'.esc($mode).'" maxlength="'.$max.'" value="'.esc($val).'" '.($res?'required':'').'></label>';
}
function reg_clients(array $reg,string $clt_id=''): void {
    echo '<label>Client<select name="client_id"><option value="">Unassigned</option>';
    foreach($reg['clients'] as $ent) echo '<option value="'.esc($ent['id']).'" '.($ent['id']===$clt_id?'selected':'').'>'.esc($ent['name']).'</option>';
    echo '</select></label>';
}
function reg_when(int $tms_act): string {return $tms_act?gmdate('Y-m-d H:i:s',$tms_act).' UTC':'Not observed';}
function reg_label(string $est): string {
    return ['ready'=>'Gateway connected','active'=>'Web terminal open','reconnecting'=>'Waiting for client / reboot',
        'awaiting_resume'=>'Restoring authorization','awaiting_client'=>'Waiting for client consent',
        'closed'=>'Authorization closed','expired'=>'Authorization expired','unknown'=>'Status unknown',
        'unavailable'=>'Case unavailable','unmonitored'=>'Direct C / offline · manual tracking'][$est]??$est;
}
?>
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>TEC · Clients, USBs and cases</title><link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="cases.css"><script src="cases.js?v=6.3.0-dev.2" defer></script></head><body class="pxe registry"><main id="registry-app" data-csrf="<?=esc($_SESSION['csrf'])?>">
<header><a class="logo" href="index.php">tec.*</a><h1>Clients, USBs &amp; support cases</h1><p>A lasting record for each visit, connection and follow-up.</p><nav><a href="cases.php">All cases</a><a href="#clients">Clients</a><a href="#usbs">Persistent USBs</a><a href="cli.php">Web terminal &amp; requests</a><a href="index.php">Account</a></nav></header>
<?php if($err!==''):?><p class="error" role="alert"><?=esc($err)?></p><?php endif?>
<?php if($msg!==''):?><p class="notice" role="status"><?=esc($msg)?></p><?php endif?>
<?php if($tec):?><details <?=$reg===null?'open':''?>><summary>Technician verification</summary><p>Signed in as <?=esc($tec['nombre'])?>. Client records belong to this technician account.</p><?php if(!isset($tec['totp_seed'])):?><a href="totp.php">Set up second factor</a><?php else:?><form method="post"><?php reg_hidden('totp');reg_input('code','TOTP code','','text',6);?><button>Verify for 15 minutes</button></form><?php endif?></details><?php else:?><p><a href="index.php#cuenta">Sign in with an approved technician account.</a></p><?php endif?>
<?php if($reg!==null):?>
<section class="summary"><div><strong><?=count($reg['clients'])?></strong><span>Clients</span></div><div><strong><?=count($reg['usbs'])?></strong><span>Persistent USBs</span></div><div><strong><?=count(array_filter($reg['cases'],fn($ent)=>$ent['workflow']!=='resolved'))?></strong><span>Open cases</span></div><div><strong><?=count(array_filter($reg['cases'],fn($ent)=>$ent['workflow']!=='resolved'&&$ent['follow_up']!==''&&$ent['follow_up']<=gmdate('Y-m-d')))?></strong><span>Follow-ups due</span></div></section>
<section id="live"><h2>Connection watch</h2><p id="registry-state" role="status">Checking gateways every 5 seconds. Times are UTC; unavailable or stale gateways show unknown.</p><form method="post" class="inline"><?php reg_hidden('sync');?><button>Refresh connections</button></form><div id="connection-list"></div></section>
<?php if($cas_sel):?><section id="case-detail"><p class="eyebrow">Case <?=esc($cas_sel['code'])?></p><h2><?=esc($cas_sel['title'])?></h2><p><span class="connection" data-case-id="<?=esc($cas_sel['id'])?>" data-state="<?=esc($cas_sel['connection'])?>"><?=esc(reg_label($cas_sel['connection']))?></span> · Last observed: <time data-seen-id="<?=esc($cas_sel['id'])?>"><?=esc(reg_when($cas_sel['last_seen']))?></time></p>
<dl><dt>Assigned technician</dt><dd><?=esc($tec['nombre'])?></dd><dt>USB</dt><dd><?php if($cas_sel['usb_id']!==''):?><a href="?usb=<?=esc(rawurlencode($cas_sel['usb_id']))?>"><?=esc($reg['usbs'][$cas_sel['usb_id']]['label'])?></a><?php else:?>Unlinked<?php endif?></dd><dt>Computer identity</dt><dd class="identity"><?=esc($cas_sel['hardware_id']?:'Not supplied')?></dd><dt>Authorization ends</dt><dd><?=esc($cas_sel['expires']?reg_when($cas_sel['expires']):'Standalone direct session')?></dd></dl>
<?php if($cas_sel['mode']==='web'):?><p><a class="button" href="cli.php?<?=esc(http_build_query(['node'=>$cas_sel['node'],'session'=>$cas_sel['session_id']]))?>">Open terminal / reconnect</a></p><form method="post"><?php reg_hidden('end_access',$cas_sel['id']);?><button>Close SSH authorization</button></form><p class="muted">Resolving a work item keeps its history. Use Close SSH authorization to end access.</p><?php else:?><p class="muted">Standalone C connections have no gateway link. Record progress here and close SSH on the client when finished.</p><?php endif?>
<form method="post"><?php reg_hidden('case_save',$cas_sel['id']);reg_input('title','Case title',$cas_sel['title'],'text',160);reg_clients($reg,$cas_sel['client_id']);?><label>Work status<select name="workflow"><?php foreach(['open'=>'Open','in_progress'=>'In progress','waiting'=>'Waiting','resolved'=>'Resolved'] as $est=>$txt):?><option value="<?=esc($est)?>" <?=$cas_sel['workflow']===$est?'selected':''?>><?=esc($txt)?></option><?php endforeach?></select></label><?php reg_input('follow_up','Follow-up date (UTC)',$cas_sel['follow_up'],'date',10,false);?><button>Save case</button></form>
<h3>Notes &amp; connection history</h3><p><a href="?case=<?=esc(rawurlencode($cas_sel['id']))?>#case-detail">Refresh history</a></p><form method="post"><?php reg_hidden('note_add',$cas_sel['id']);?><label>Work note<textarea name="note" rows="4" maxlength="4000" required></textarea></label><button>Add note</button></form><ol class="timeline"><?php $lst=array_filter($reg['events'],fn($evt)=>$evt['case_id']===$cas_sel['id']);uasort($lst,fn($ent,$val)=>$val['at']<=>$ent['at']);foreach($lst as $evt):?><li><time><?=esc(reg_when($evt['at']))?></time><strong><?=esc(str_replace('_',' ',$evt['event']))?></strong><p><?=nl2br(esc($evt['text']))?></p></li><?php endforeach?></ol></section><?php endif?>
<section id="cases"><h2><?=esc($clt_sel?'Cases for '.$clt_sel['name']:($usb_sel?'Cases for '.$usb_sel['label']:'Case register'))?></h2>
<form method="get" class="filters"><?php if($clt_sel):?><input type="hidden" name="client" value="<?=esc($clt_sel['id'])?>"><?php endif?><?php if($usb_sel):?><input type="hidden" name="usb" value="<?=esc($usb_sel['id'])?>"><?php endif?><?php reg_input('q','Search',is_string($_GET['q']??null)?substr($_GET['q'],0,120):'','search',120,false);?><label>Work status<select name="filter"><?php foreach(['all'=>'All','open'=>'Open work','due'=>'Follow-up due','resolved'=>'Resolved'] as $est=>$txt):?><option value="<?=esc($est)?>" <?=($_GET['filter']??'all')===$est?'selected':''?>><?=esc($txt)?></option><?php endforeach?></select></label><button>Filter cases</button></form>
<?php $qry=is_string($_GET['q']??null)?strtolower(substr($_GET['q'],0,120)):'';$flt=$_GET['filter']??'all';$lst=$reg['cases'];uasort($lst,fn($ent,$val)=>$val['updated']<=>$ent['updated']);$cnt_reg=0;foreach($lst as $ent):
    $clt=$reg['clients'][$ent['client_id']]??[];$usb_sel=$reg['usbs'][$ent['usb_id']]??[];
    if($clt_sel&&$ent['client_id']!==$clt_sel['id'])continue;
    if(isset($_GET['usb'])&&$ent['usb_id']!==$_GET['usb'])continue;
    if($qry!==''&&!str_contains(strtolower(implode(' ',[$ent['title'],$ent['code'],$clt['name']??'',$usb_sel['label']??'',$usb_sel['usb_uuid']??'',$ent['hardware_id']])),$qry))continue;
    if(($flt==='open'&&$ent['workflow']==='resolved')||($flt==='resolved'&&$ent['workflow']!=='resolved')||($flt==='due'&&($ent['workflow']==='resolved'||$ent['follow_up']===''||$ent['follow_up']>gmdate('Y-m-d'))))continue;
    $cnt_reg++;?><article class="case-card"><h3><a href="?case=<?=esc(rawurlencode($ent['id']))?>"><?=esc($ent['title'])?></a></h3><p><?=esc($clt['name']??'Client unassigned')?> · <?=esc($usb_sel['label']??'USB unlinked')?></p><p><span class="connection" data-case-id="<?=esc($ent['id'])?>" data-state="<?=esc($ent['connection'])?>"><?=esc(reg_label($ent['connection']))?></span> · <?=esc(str_replace('_',' ',$ent['workflow']))?><?php if($ent['follow_up']!==''):?> · Follow-up <?=esc($ent['follow_up'])?><?php endif?></p><p class="muted"><?=esc($ent['code'])?> · Last observed: <time data-seen-id="<?=esc($ent['id'])?>"><?=esc(reg_when($ent['last_seen']))?></time></p></article><?php endforeach?><?php if(!$cnt_reg):?><p>No matching cases. Web cases appear after accepting a client request. Existing pre-update cases are recorded when they reconnect.</p><?php endif?></section>
<section id="clients"><h2>Client register</h2><form method="post"><?php reg_hidden('import_requests');?><button>Import clients from my confirmed requests</button></form><div class="registry-grid"><div><h3><?=esc($clt_sel?'Edit client':'Add client')?></h3><form method="post"><?php reg_hidden('client_save',$clt_sel['id']??'');reg_input('name','Name',$clt_sel['name']??'');reg_input('email','Email',$clt_sel['email']??'','email',254,false);reg_input('phone','Phone',$clt_sel['phone']??'','tel',40,false);reg_input('reference','Reference / company',$clt_sel['reference']??'','text',120,false);?><button>Save client</button></form></div><div><?php foreach($reg['clients'] as $clt):?><article><h3><a href="?client=<?=esc(rawurlencode($clt['id']))?>"><?=esc($clt['name'])?></a></h3><p><?=esc($clt['reference'])?></p><p><?=esc($clt['email'])?> · <?=esc($clt['phone'])?></p></article><?php endforeach?></div></div></section>
<?php $usb_sel=isset($_GET['usb'])?$reg['usbs'][$_GET['usb']]:null;?>
<section id="usbs"><h2>Persistent USB register</h2><p>Register the ext4 persistent filesystem UUID before a visit, or assign an automatically discovered USB after consent. The same USB can have cases on different computers.</p><div class="registry-grid"><div><h3><?=esc($usb_sel?'Edit USB':'Register USB')?></h3><form method="post"><?php reg_hidden('usb_save',$usb_sel['id']??'');reg_input('label','USB label',$usb_sel['label']??'');reg_input('usb_uuid','Persistent filesystem UUID',$usb_sel['usb_uuid']??'','text',36);reg_clients($reg,$usb_sel['client_id']??'');?><label>Inventory state<select name="lifecycle"><?php foreach(['active','lost','retired'] as $est):?><option value="<?=esc($est)?>" <?=($usb_sel['lifecycle']??'active')===$est?'selected':''?>><?=esc(ucfirst($est))?></option><?php endforeach?></select></label><button>Save USB</button></form><p class="muted">Client assignment applies to future cases. Existing cases retain their client. Inventory state alone does not revoke an active SSH authorization.</p></div><div><?php foreach($reg['usbs'] as $ent):?><article><h3><a href="?usb=<?=esc(rawurlencode($ent['id']))?>"><?=esc($ent['label'])?></a></h3><p><?=esc($reg['clients'][$ent['client_id']]['name']??'Client unassigned')?> · <?=esc($ent['lifecycle'])?></p><p class="identity"><?=esc($ent['usb_uuid'])?></p><p>Last observed: <?=esc(reg_when($ent['last_seen']??0))?></p></article><?php endforeach?></div></div></section>
<section><h2>Record C / offline work</h2><p>Keep direct SSH visits in the same history. Connection status is marked as manually tracked.</p><form method="post"><?php reg_hidden('manual_case');reg_input('title','Case title','','text',160);reg_clients($reg);?><label>USB<select name="usb_id"><option value="">Unlinked</option><?php foreach($reg['usbs'] as $ent):?><option value="<?=esc($ent['id'])?>"><?=esc($ent['label'])?></option><?php endforeach?></select></label><button>Create case</button></form></section>
<?php endif?><footer><a href="https://www.alawise.es/1-s">Credits, concept &amp; architecture</a> · 6.3.0-dev.2</footer></main></body></html>
