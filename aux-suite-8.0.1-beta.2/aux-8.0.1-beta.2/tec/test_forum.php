<?php
/** Timestamp: 2026-11-23 | Version: 8.0.1-beta.2
 * Author & Credits: https://www.alawise.es/1-s
 * Exercise native persistence and permissions without any real accounts or mail.
 */
declare(strict_types=1);
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
define('AUX_ASSIST_ENTRY',true);require __DIR__.'/web/lib.php';require __DIR__.'/web/forum-lib.php';
function chk(bool $ok,string $msg):void{if(!$ok)throw new RuntimeException($msg);}
function rechaza(callable $fn):void{try{$fn();}catch(InvalidArgumentException $e){return;}throw new RuntimeException('Invalid action accepted.');}
$pth=$argv[1]??'';if($pth===''||!is_dir($pth)||glob($pth.'/*'))throw new RuntimeException('Supply an empty private test directory.');
putenv('AUX_ASSIST_DATA_DIR='.$pth);
$usr=['id'=>'usr_author','nombre'=>'Author','estado'=>'activo','email_confirmado'=>true];$adm=['id'=>'usr_admin','nombre'=>'Moderator','estado'=>'activo','email_confirmado'=>true];
datos(function(&$d)use($usr,$adm){$d['usuarios']=[$usr,$adm];},true);
$frm=['name'=>'Public author','title'=>'Rescue procedure','category'=>'recipe','evidence'=>'simulated','system'=>'Test Linux','release'=>'1.0','architecture'=>'x86_64','firmware'=>'UEFI VM','body'=>'<script>test</script>','commands'=>'printf test','proof'=>'Virtual machine test with a recorded expected result.','sources'=>'https://example.test/docs'];
rechaza(fn()=>foro_action(null,'topic',$frm));rechaza(fn()=>foro_action(['id'=>'spoof'],'topic',$frm));rechaza(fn()=>foro_action($usr,'topic',array_replace($frm,['sources'=>'javascript:alert(1)'])));
$slug=foro_action($usr,'topic',$frm);$dat=foro_store(fn($d)=>$d);$ent=array_values($dat['topics'])[0];
chk($ent['status']==='pending'&&!foro_visible($dat,$ent,null)&&!foro_visible($dat,$ent,$adm)&&foro_visible($dat,$ent,$usr),'Pending topic visibility failed.');
$rev=['kind'=>'topic','id'=>$ent['id'],'status'=>'published','note'=>'Environment and sources reviewed.'];rechaza(fn()=>foro_action($usr,'review',$rev));
foro_rol($adm['id'],true);foro_action($adm,'review',$rev);$dat=foro_store(fn($d)=>$d);chk(foro_visible($dat,$dat['topics'][$ent['id']],null),'Published topic hidden.');
foro_action($usr,'reply',['name'=>'Public author','topic'=>$ent['id'],'body'=>'Independent test result']);$dat=foro_store(fn($d)=>$d);$r=array_values($dat['replies'])[0];chk(!foro_visible($dat,$r,null),'Pending reply leaked.');
foro_action($adm,'review',['kind'=>'reply','id'=>$r['id'],'status'=>'published','note'=>'Reply checked.']);$dat=foro_store(fn($d)=>$d);chk(foro_visible($dat,$dat['replies'][$r['id']],null),'Published reply hidden.');
chk(count($dat['reviews'])===2,'Review audit missing.');chk((fileperms($pth.'/forum.json')&0777)===0600,'Forum JSON permissions incorrect.');
chk(str_contains(esc($ent['body']),'&lt;script&gt;'),'Markup escaping failed.');
datos(function(&$d){$d['usuarios'][1]['estado']='suspendido';},true);rechaza(fn()=>foro_action($adm,'review',$rev));
echo "Native forum: confirmed identity, private drafts, moderation, replies, persistence, audit and escaping passed.\n";
