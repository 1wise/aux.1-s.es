<?php
/** Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * Test durable client links, event replay and cross-technician access boundaries.
 */
declare(strict_types=1);
if(PHP_SAPI!=='cli')exit(1);
define('AUX_ASSIST_ENTRY',true);require __DIR__.'/web/lib.php';require __DIR__.'/web/registry-lib.php';
function check(bool $val,string $txt):void{if(!$val)throw new RuntimeException($txt);}
function rejected(callable $fn,string $txt):void{try{$fn();}catch(InvalidArgumentException $err){return;}throw new RuntimeException($txt);}
$tec=['id'=>'tec_fixture'];$ent=['id'=>'tec_other'];
$clt_id=reg_action($tec,'client_save',['name'=>'Client <fixture>','email'=>'client@example.test','phone'=>'+34123456789','reference'=>'Fixture']);
$usb_id=reg_action($tec,'usb_save',['label'=>'USB One','usb_uuid'=>'12345678-1234-4321-8765-123456789abc','client_id'=>$clt_id,'lifecycle'=>'active']);
rejected(fn()=>reg_action($ent,'usb_save',['id'=>$usb_id]),'Cross-owner USB mutation');
rejected(fn()=>reg_action($ent,'manual_case',['title'=>'Cross-owner','client_id'=>$clt_id]),'Cross-owner client link');
rejected(fn()=>reg_action($tec,'usb_save',['label'=>'Duplicate','usb_uuid'=>'12345678-1234-4321-8765-123456789abc','lifecycle'=>'active']),'Duplicate USB accepted');
function fixture(int $seq_evt,string $id,string $est='ready'):array{return ['node'=>'fixture','events'=>[['seq'=>$seq_evt,'node'=>'fixture','event'=>'authorized','at'=>time(),'reason'=>'',
    'session'=>['id'=>$id,'code'=>'AUX-FIXTURE','created'=>time()-30,'expires'=>time()+120,'state'=>$est,
    'device'=>['usb_uuid'=>'12345678-1234-4321-8765-123456789abc','hardware_id'=>'a'.str_repeat('1',63)]]]],'cursor'=>$seq_evt,'more'=>false];}
$cas_id='fixture:'.str_repeat('a',32);
check(reg_ingest($tec,'fixture',fixture(1,str_repeat('a',32)))===1,'Initial import');
check(reg_ingest($tec,'fixture',fixture(1,str_repeat('a',32)))===0,'Idempotent replay');
$reg=reg_view($tec);
check(count($reg['usbs'])===1&&$reg['cases'][$cas_id]['client_id']===$clt_id,'Known USB inherits client');
reg_action($tec,'case_save',['id'=>$cas_id,'title'=>'Repair work','client_id'=>$clt_id,'workflow'=>'waiting','follow_up'=>'2026-10-18']);
reg_action($tec,'note_add',['id'=>$cas_id,'note'=>"Work completed\n<script>fixture</script>"]);
reg_ingest($tec,'fixture',fixture(2,str_repeat('a',32),'reconnecting'));
$reg=reg_view($tec);
check($reg['cases'][$cas_id]['title']==='Repair work'&&$reg['cases'][$cas_id]['workflow']==='waiting','Sync clobbered work details');
check(count($reg['events'])===4,'Events or notes lost');
reg_live($tec,'fixture',['sessions'=>[['id'=>str_repeat('a',32),'state'=>'ready','expires'=>time()+120]]]);
check(reg_view($tec)['cases'][$cas_id]['connection']==='ready','Live state');
reg_live($tec,'fixture',null);
check(reg_view($tec)['cases'][$cas_id]['connection']==='unknown','Offline gateway claimed online');
reg_ingest($tec,'fixture',fixture(3,str_repeat('a',32),'closed'));
check(reg_view($tec)['cases'][$cas_id]['connection']==='closed','Closed authorization disappeared');
rejected(fn()=>reg_action($ent,'note_add',['id'=>$cas_id,'note'=>'Cross-owner']),'Cross-owner note');
rejected(fn()=>reg_action($tec,'case_save',['id'=>$cas_id,'title'=>'Bad date','client_id'=>$clt_id,'workflow'=>'open','follow_up'=>'2026-02-30']),'Impossible date accepted');
$reg=reg_view($ent);check(!$reg['clients']&&!$reg['usbs']&&!$reg['cases']&&!$reg['events']&&!$reg['nodes'],'Cross-owner data leak');
$clt_sel=reg_action($tec,'client_save',['name'=>'Second client']);
reg_action($tec,'usb_save',['id'=>$usb_id,'label'=>'USB One','usb_uuid'=>'12345678-1234-4321-8765-123456789abc','client_id'=>$clt_sel,'lifecycle'=>'active']);
reg_ingest($tec,'fixture',fixture(4,str_repeat('b',32)));
$reg=reg_view($tec);
check($reg['cases'][$cas_id]['client_id']===$clt_id,'Reassignment rewrote client history');
check($reg['cases']['fixture:'.str_repeat('b',32)]['client_id']===$clt_sel,'New approval did not follow USB assignment');
$id=reg_action($tec,'manual_case',['title'=>'Direct SSH visit','usb_id'=>$usb_id]);
check(reg_view($tec)['cases'][$id]['connection']==='unmonitored','Direct session claimed live status');
check((fileperms(pth_datos().'/registry.json')&0777)===0600,'Private record file permissions');
datos(function(&$dat){$dat['solicitudes']=[['id'=>'sol_fixture','tecnico_id'=>'tec_fixture','cliente'=>'Imported Client',
    'cliente_correo'=>'imported@example.test','cliente_telefono'=>'+34111222333','email_confirmado'=>true],
    ['id'=>'sol_other','tecnico_id'=>'tec_other','cliente'=>'Other Private Client','cliente_correo'=>'private@example.test',
    'cliente_telefono'=>'+34111222334','email_confirmado'=>true],
    ['id'=>'sol_unconfirmed','tecnico_id'=>'tec_fixture','cliente'=>'Unconfirmed Client','cliente_correo'=>'pending@example.test',
    'cliente_telefono'=>'+34111222335','email_confirmado'=>false]];},true);
check(reg_import_requests($tec)===1,'Import included another technician or unconfirmed request');
check(reg_import_requests($tec)===0,'Repeated request import duplicated a client');
echo "PASS: client/USB/case registry, replay, follow-up, notes, history retention, reassignment and technician isolation\n";
