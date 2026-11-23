<?php
/** Timestamp: 2026-11-23 | Version: 8.0.1-beta.3
 * Author & Credits: https://www.alawise.es/1-s
 * Check the three-board contract without changing a catalogue or using real users.
 */
declare(strict_types=1);
if(PHP_SAPI!=='cli')exit(1);
define('AUX_ASSIST_ENTRY',true);
require __DIR__.'/web/lib.php';require __DIR__.'/web/forum-lib.php';
$pth=$argv[1]??'';
if($pth===''||!is_dir($pth)||glob($pth.'/*'))throw new RuntimeException('Supply an empty test directory.');
putenv('AUX_ASSIST_DATA_DIR='.$pth);
function ok(bool $v,string $s):void{if(!$v)throw new RuntimeException($s);}
$usr=['id'=>'usr_fixture','nombre'=>'Fixture','estado'=>'activo','email_confirmado'=>true];
datos(function(&$d)use($usr){$d['usuarios']=[$usr];},true);
foreach(['urls','deploy','pxe'] as $board){
    $frm=['name'=>'Test author','title'=>'Question for '.$board,'board'=>$board,'category'=>'question',
          'evidence'=>'hypothesis','body'=>'Where is this artifact documented?'];
    if($board==='deploy')$frm['policy12']='E16';
    foro_action($usr,'topic',$frm);
}
$dat=foro_store(fn($d)=>$d);ok(count($dat['topics'])===3,'Three topics required.');
$boards=[];
foreach($dat['topics'] as $ent){$boards[]=$ent['board'];ok($ent['status']==='pending','Questions must await moderation.');}
sort($boards);ok($boards===['deploy','pxe','urls'],'Board persistence failed.');
foreach([['board'=>'urls','policy12'=>'E16'],['board'=>'deploy','policy12'=>'0E16'],['board'=>'deploy','policy12'=>'ZZZ']] as $bad){
    $caught=false;
    try{foro_action($usr,'topic',array_replace($frm,$bad));}catch(InvalidArgumentException $exc){$caught=true;}
    ok($caught,'Invalid policy accepted.');
}
echo "AUX 8 forums: three boards, optional question fields, pending moderation and policy validation passed.\n";
