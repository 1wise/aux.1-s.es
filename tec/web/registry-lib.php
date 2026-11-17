<?php
/** Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Keep business records after transport capabilities expire or are revoked.
 */
declare(strict_types=1);
if (!defined('AUX_ASSIST_ENTRY')) { http_response_code(404); exit; }

function reg_store(callable $fn, bool $res=false) {
    $pth=pth_datos();
    if(!is_dir($pth)) datos(fn($dat)=>null);
    $fd=fopen($pth.'/.registry.lock','c+');
    if($fd===false||!flock($fd,$res?LOCK_EX:LOCK_SH)) throw new RuntimeException('Cannot lock client register.');
    chmod($pth.'/.registry.lock',0600);
    $pth_reg=$pth.'/registry.json';
    try {
        $reg=['schema'=>1,'clients'=>[],'usbs'=>[],'cases'=>[],'events'=>[],'cursors'=>[],'nodes'=>[]];
        if(is_file($pth_reg)) {
            if(filesize($pth_reg)>67108864) throw new RuntimeException('Registry requires archival before further updates.');
            $reg=json_decode((string)file_get_contents($pth_reg),true,64,JSON_THROW_ON_ERROR);
            if(!is_array($reg)||($reg['schema']??null)!==1) throw new RuntimeException('Unsupported registry schema.');
            foreach(['clients','usbs','cases','events','cursors','nodes'] as $nom)
                if(!is_array($reg[$nom]??null)) throw new RuntimeException('Invalid registry structure.');
        }
        $dat=$fn($reg);
        if($res) {
            $txt=json_encode($reg,JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR)."\n";
            $tmp=tempnam($pth,'.registry-');
            if($tmp===false) throw new RuntimeException('Cannot create registry update.');
            try {
                chmod($tmp,0600);
                if(file_put_contents($tmp,$txt)!==strlen($txt)) throw new RuntimeException('Incomplete registry update.');
                $arc=fopen($tmp,'r+');
                if($arc===false||!fflush($arc)||(function_exists('fsync')&&!fsync($arc))) throw new RuntimeException('Cannot flush registry update.');
                fclose($arc);
                if(!rename($tmp,$pth_reg)) throw new RuntimeException('Cannot replace registry.');
            } finally { if(is_file($tmp)) unlink($tmp); }
        }
        return $dat;
    } finally { flock($fd,LOCK_UN);fclose($fd); }
}
function reg_field(array $dat,string $nom,int $max,bool $oblig=true,bool $res=false): string {
    $txt=$dat[$nom]??'';
    if(!is_string($txt)) throw new InvalidArgumentException('Invalid field: '.$nom);
    $txt=trim($txt);
    if(($oblig&&$txt==='')||strlen($txt)>$max||!preg_match('//u',$txt)||
       preg_match('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/',$txt)||(!$res&&preg_match('/[\r\n\t]/',$txt)))
        throw new InvalidArgumentException('Invalid field: '.$nom);
    return $txt;
}
function reg_owned(array $reg,string $nom,string $id,array $tec): array {
    $ent=$reg[$nom][$id]??null;
    if(!is_array($ent)||($ent['tech_id']??'')!==$tec['id']) throw new InvalidArgumentException('Record unavailable.');
    return $ent;
}
function reg_client(array $reg,string $clt_id,array $tec): void {
    if($clt_id!=='') reg_owned($reg,'clients',$clt_id,$tec);
}
function reg_note(array &$reg,string $cas_id,array $tec,string $txt,string $nom='note'): void {
    $evt_id='note_'.bin2hex(random_bytes(12));
    $reg['events'][$evt_id]=['id'=>$evt_id,'case_id'=>$cas_id,'tech_id'=>$tec['id'],
        'event'=>$nom,'at'=>time(),'text'=>$txt];
}
function reg_action(array $tec,string $act,array $dat): string {
    return reg_store(function(&$reg)use($tec,$act,$dat){
        $id=reg_field($dat,'id',96,false);
        if($act==='client_save') {
            $ent=$id!==''?reg_owned($reg,'clients',$id,$tec):['id'=>'clt_'.bin2hex(random_bytes(12)),
                'tech_id'=>$tec['id'],'created'=>time()];
            $ent['name']=reg_field($dat,'name',120);
            $ent['email']=reg_field($dat,'email',254,false);
            if($ent['email']!==''&&!filter_var($ent['email'],FILTER_VALIDATE_EMAIL)) throw new InvalidArgumentException('Invalid email address.');
            $ent['phone']=reg_field($dat,'phone',40,false);
            $ent['reference']=reg_field($dat,'reference',120,false);
            $ent['updated']=time();$reg['clients'][$ent['id']]=$ent;return $ent['id'];
        }
        if($act==='usb_save') {
            $ent=$id!==''?reg_owned($reg,'usbs',$id,$tec):['id'=>'usb_'.bin2hex(random_bytes(12)),
                'tech_id'=>$tec['id'],'created'=>time(),'client_id'=>''];
            $uid_usb=strtolower(reg_field($dat,'usb_uuid',36));
            if(!preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/',$uid_usb))
                throw new InvalidArgumentException('Enter the persistent filesystem UUID, not the USB label.');
            if(isset($ent['usb_uuid'])&&$ent['usb_uuid']!==$uid_usb) throw new InvalidArgumentException('A USB identity cannot be changed.');
            foreach($reg['usbs'] as $usb_sel) if($usb_sel['tech_id']===$tec['id']&&$usb_sel['usb_uuid']===$uid_usb&&$usb_sel['id']!==$ent['id'])
                throw new InvalidArgumentException('This USB is already registered.');
            $ent['label']=reg_field($dat,'label',120);$ent['usb_uuid']=$uid_usb;
            $ent['client_id']=reg_field($dat,'client_id',64,false);reg_client($reg,$ent['client_id'],$tec);
            $ent['lifecycle']=reg_field($dat,'lifecycle',16);
            if(!in_array($ent['lifecycle'],['active','lost','retired'],true)) throw new InvalidArgumentException('Invalid USB state.');
            $ent['updated']=time();$reg['usbs'][$ent['id']]=$ent;return $ent['id'];
        }
        if($act==='manual_case') {
            $usb_id=reg_field($dat,'usb_id',64,false);
            $usb_sel=$usb_id!==''?reg_owned($reg,'usbs',$usb_id,$tec):null;
            $clt_id=reg_field($dat,'client_id',64,false);
            if($clt_id==='') $clt_id=$usb_sel['client_id']??'';
            reg_client($reg,$clt_id,$tec);$id='manual:'.bin2hex(random_bytes(16));
            $reg['cases'][$id]=['id'=>$id,'tech_id'=>$tec['id'],'node'=>'','session_id'=>'',
                'code'=>'C-'.strtoupper(substr($id,-8)),'created'=>time(),'expires'=>0,
                'title'=>reg_field($dat,'title',160),'workflow'=>'open','follow_up'=>'',
                'client_id'=>$clt_id,'usb_id'=>$usb_id,'hardware_id'=>'','state'=>'unmonitored',
                'mode'=>'direct_manual','updated'=>time(),'last_seen'=>0,'checked_at'=>0];
            reg_note($reg,$id,$tec,'Direct C / offline work recorded manually.','recorded');return $id;
        }
        $ent=reg_owned($reg,'cases',$id,$tec);
        if($act==='case_save') {
            $clt_id=reg_field($dat,'client_id',64,false);reg_client($reg,$clt_id,$tec);
            $ent['title']=reg_field($dat,'title',160);$ent['client_id']=$clt_id;
            $ent['workflow']=reg_field($dat,'workflow',20);
            if(!in_array($ent['workflow'],['open','in_progress','waiting','resolved'],true)) throw new InvalidArgumentException('Invalid workflow state.');
            $ent['follow_up']=reg_field($dat,'follow_up',10,false);
            if($ent['follow_up']!=='') {
                $val=DateTimeImmutable::createFromFormat('!Y-m-d',$ent['follow_up'],new DateTimeZone('UTC'));
                if(!$val||$val->format('Y-m-d')!==$ent['follow_up']) throw new InvalidArgumentException('Invalid follow-up date.');
            }
            $ent['updated']=time();
            if($ent!==$reg['cases'][$id]) reg_note($reg,$id,$tec,'Case details updated; workflow: '.$ent['workflow'].'.','updated');
            $reg['cases'][$id]=$ent;return $id;
        }
        if($act==='note_add') {
            reg_note($reg,$id,$tec,reg_field($dat,'note',4000,true,true));return $id;
        }
        throw new InvalidArgumentException('Unknown register action.');
    },true);
}
function reg_import_requests(array $tec): int {
    $lst=solicitudes_tecnico($tec);
    return reg_store(function(&$reg)use($tec,$lst){
        $cnt_reg=0;
        foreach($lst as $ent) {
            $res=false;
            foreach($reg['clients'] as $clt) if($clt['tech_id']===$tec['id']&&strtolower($clt['email'])===strtolower($ent['cliente_correo'])) {$res=true;break;}
            if($res)continue;
            $clt_id='clt_'.bin2hex(random_bytes(12));
            $reg['clients'][$clt_id]=['id'=>$clt_id,'tech_id'=>$tec['id'],'created'=>time(),'updated'=>time(),
                'name'=>$ent['cliente'],'email'=>$ent['cliente_correo'],'phone'=>$ent['cliente_telefono'],'reference'=>''];
            $cnt_reg++;
        }
        return $cnt_reg;
    },true);
}

function reg_ingest(array $tec,string $nom,array $dat): int {
    // The signed gateway response identifies ownership. A USB UUID is only a label.
    if(($dat['node']??'')!==$nom||!is_array($dat['events']??null)||count($dat['events'])>200)
        throw new RuntimeException('Invalid gateway history.');
    return reg_store(function(&$reg)use($tec,$nom,$dat){
        $key=$tec['id'].'@'.$nom;$cur_evt=$reg['cursors'][$key]??0;$cnt_evt=0;
        foreach($dat['events'] as $evt) {
            if(!is_int($evt['seq']??null)||$evt['seq']<1||!is_array($evt['session']??null)) throw new RuntimeException('Invalid history event.');
            if($evt['seq']<=$cur_evt) continue;
            $ses=$evt['session'];$cas_id=$nom.':'.reg_field($ses,'id',32);
            if(!preg_match('/^[a-f0-9]{32}$/',$ses['id'])||($evt['node']??'')!==$nom) throw new RuntimeException('Invalid history case.');
            $evt_id=$key.':'.$evt['seq'];
            $ent=$reg['cases'][$cas_id]??['id'=>$cas_id,'tech_id'=>$tec['id'],'node'=>$nom,
                'session_id'=>$ses['id'],'code'=>reg_field($ses,'code',64),'created'=>(int)$ses['created'],
                'title'=>reg_field($ses,'code',64),'workflow'=>'open','follow_up'=>'','client_id'=>'',
                'usb_id'=>'','hardware_id'=>'','mode'=>'web','last_seen'=>0,'checked_at'=>0];
            if($ent['tech_id']!==$tec['id']) throw new RuntimeException('History ownership conflict.');
            $ent['state']=reg_field($ses,'state',32);$ent['expires']=(int)$ses['expires'];
            $ent['updated']=(int)$evt['at'];
            $uid_usb=$ses['device']['usb_uuid']??'';
            if($uid_usb!==''&&preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/',$uid_usb)) {
                $usb_id='';
                foreach($reg['usbs'] as $usb_sel) if($usb_sel['tech_id']===$tec['id']&&$usb_sel['usb_uuid']===$uid_usb) {$usb_id=$usb_sel['id'];break;}
                if($usb_id==='') {
                    $usb_id='usb_'.bin2hex(random_bytes(12));
                    $reg['usbs'][$usb_id]=['id'=>$usb_id,'tech_id'=>$tec['id'],'usb_uuid'=>$uid_usb,
                        'label'=>'USB '.substr($uid_usb,-8),'client_id'=>'','lifecycle'=>'active','created'=>(int)$evt['at']];
                }
                if($ent['usb_id']==='') {
                    $ent['usb_id']=$usb_id;
                    if($ent['client_id']==='') $ent['client_id']=$reg['usbs'][$usb_id]['client_id'];
                }
                $reg['usbs'][$usb_id]['last_seen']=max($reg['usbs'][$usb_id]['last_seen']??0,(int)$evt['at']);
                $ent['hardware_id']=reg_field($ses['device'],'hardware_id',64);
            }
            if(in_array($ent['state'],['ready','active'],true)) $ent['last_seen']=(int)$evt['at'];
            $reg['cases'][$cas_id]=$ent;
            $reg['events'][$evt_id]=['id'=>$evt_id,'case_id'=>$cas_id,'tech_id'=>$tec['id'],
                'event'=>reg_field($evt,'event',48),'at'=>(int)$evt['at'],
                'text'=>reg_field($evt,'reason',120,false),'state'=>$ent['state']];
            $cnt_evt++;$cur_evt=$evt['seq'];
        }
        // Commit the cursor with its records, so a crash can safely replay a page.
        $reg['cursors'][$key]=$cur_evt;return $cnt_evt;
    },true);
}
function reg_live(array $tec,string $nom,?array $dat): void {
    reg_store(function(&$reg)use($tec,$nom,$dat){
        $key=$tec['id'].'@'.$nom;
        $reg['nodes'][$key]=['online'=>$dat!==null,'checked_at'=>time()];
        if($dat===null) return;
        foreach($reg['cases'] as &$ent) if($ent['tech_id']===$tec['id']&&$ent['node']===$nom) {
            $ses=null;
            foreach($dat['sessions']??[] as $val) if($val['id']===$ent['session_id']) {$ses=$val;break;}
            if($ses) {
                $ent['state']=$ses['state'];$ent['expires']=(int)$ses['expires'];$ent['checked_at']=time();
                if(in_array($ent['state'],['ready','active'],true)) {
                    $ent['last_seen']=time();
                    if($ent['usb_id']!=='') $reg['usbs'][$ent['usb_id']]['last_seen']=time();
                }
            } elseif($ent['state']!=='closed') {
                $ent['state']=$ent['expires']<=time()?'expired':'unavailable';$ent['checked_at']=time();
            }
        } unset($ent);
    },true);
}
function reg_sync(array $tec): array {
    $res_sync=[];
    foreach((config_proyecto()['cli']['enabled']??false)?(config_proyecto()['cli']['nodes']??[]):[] as $nom=>$cfg) {
        try {
            $cur_evt=reg_store(fn($reg)=>$reg['cursors'][$tec['id'].'@'.$nom]??0);
            $dat=cli_api($tec,$nom,'/api/history?cursor='.$cur_evt);
            reg_ingest($tec,$nom,$dat);
            reg_live($tec,$nom,cli_api($tec,$nom,'/api/sessions'));
            $res_sync[$nom]=($dat['more']??false)?'catching_up':'online';
        } catch(Throwable $err) {
            error_log('TEC registry sync '.$nom.': '.$err->getMessage());
            reg_live($tec,$nom,null);$res_sync[$nom]='unavailable';
        }
    }
    return $res_sync;
}
function reg_state(array $ent,array $reg): string {
    if($ent['mode']==='direct_manual') return 'unmonitored';
    if($ent['state']==='closed') return 'closed';
    if($ent['expires']<=time()) return 'expired';
    $dat=$reg['nodes'][$ent['tech_id'].'@'.$ent['node']]??[];
    if(!($dat['online']??false)||time()-($dat['checked_at']??0)>30) return 'unknown';
    if(time()-($ent['checked_at']??0)>30) return 'unknown';
    return $ent['state'];
}
function reg_view(array $tec): array {
    return reg_store(function($reg)use($tec){
        foreach(['clients','usbs','cases','events'] as $nom)
            $reg[$nom]=array_filter($reg[$nom],fn($ent)=>$ent['tech_id']===$tec['id']);
        $reg['nodes']=array_filter($reg['nodes'],fn($key)=>str_starts_with($key,$tec['id'].'@'),ARRAY_FILTER_USE_KEY);
        $reg['cursors']=[];
        foreach($reg['cases'] as &$ent) $ent['connection']=reg_state($ent,$reg);
        unset($ent);return $reg;
    });
}
