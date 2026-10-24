<?php
/** Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
 * Author and Credits: https://www.alawise.es/1-s
 * Serve a dedicated workspace only after the existing account and TOTP checks.
 */
declare(strict_types=1);
define('AUX_ASSIST_ENTRY',true);require __DIR__.'/lib.php';require __DIR__.'/cli-lib.php';
if(($_SERVER['HTTPS']??'')!=='on'){http_response_code(403);exit('HTTPS required.');}
header('Cache-Control: no-store');header('Referrer-Policy: no-referrer');header('X-Content-Type-Options: nosniff');
session_name('tec_assist');session_set_cookie_params(['secure'=>true,'httponly'=>true,'samesite'=>'Lax','path'=>'/']);session_start();
$_SESSION['csrf']??=bin2hex(random_bytes(32));
$err='';$nom='';$id='';$url='';$ses=null;
try{
    $tec=cli_auth();cli_lease($tec);$cfg=cli_cfg();
    $nom=$_GET['node']??$cfg['primary'];$id=$_GET['session']??'';
    if(!is_string($nom)||!is_string($id)||!preg_match('/^[a-f0-9]{32}$/',$id))throw new InvalidArgumentException('Invalid case.');
    $ent=cli_node($nom);$url=$ent['url'];
    // Pending requests are public to technicians; a workspace needs an assigned case.
    foreach(cli_api($tec,$nom,'/api/sessions')['sessions'] as $ent){
        if($ent['id']===$id&&$ent['state']!=='pending'){$ses=$ent;break;}
    }
    if($ses===null)throw new InvalidArgumentException('Case unavailable for this technician.');
}catch(Throwable $exc){http_response_code(403);$err=$exc->getMessage();$url='';}
$nom=is_string($nom)?$nom:'';$id=is_string($id)?$id:'';
session_write_close();
$connect=$url!==''?' '.str_replace('https://','wss://',$url):'';
// xterm calculates its grid using dynamic styles; executable code stays same-origin.
header("Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'".$connect."; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
?>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>TEC · Two terminals</title><link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="vendor/xterm.css"><link rel="stylesheet" href="terminal.css"><script src="vendor/xterm.js" defer></script><script src="terminal.js?v=6.4.0-dev.1" defer></script></head>
<body class="pxe terminal-workspace"><main id="terminal-app" data-csrf="<?=esc($_SESSION['csrf'])?>" data-node="<?=esc($nom)?>" data-session="<?=esc($id)?>" data-url="<?=esc($url)?>">
<header class="workspace-header"><a class="logo" href="index.php">tec.*</a><div><h1><?=esc($ses['code']??'Terminal workspace')?></h1><p><?=esc($nom)?> · Two independent terminals · <?=esc(ASIST_VERSION)?></p></div><a class="workspace-back" href="cli.php?node=<?=esc($nom)?>">Requests &amp; authorization</a></header>
<?php if($err):?><p class="error" role="alert"><?=esc($err)?></p><?php else:?>
<p id="terminal-state" role="status" aria-live="polite">Connecting to the authorized case…</p>
<div class="terminal-tabs" role="tablist" aria-label="Remote terminals">
<?php foreach([1,2] as $idx_trm):?><button type="button" role="tab" id="terminal-tab-<?=$idx_trm?>" aria-controls="terminal-panel-<?=$idx_trm?>" aria-selected="<?=$idx_trm===1?'true':'false'?>" tabindex="<?=$idx_trm===1?'0':'-1'?>">Terminal <?=$idx_trm?></button><?php endforeach?>
</div>
<?php foreach([1,2] as $idx_trm):?>
<section id="terminal-panel-<?=$idx_trm?>" class="terminal-panel" role="tabpanel" aria-labelledby="terminal-tab-<?=$idx_trm?>" <?=$idx_trm===2?'hidden':''?>>
<div class="terminal-toolbar"><span id="terminal-status-<?=$idx_trm?>">Waiting for connection</span><div><button type="button" id="terminal-paste-<?=$idx_trm?>" disabled>Paste</button><button type="button" id="terminal-interrupt-<?=$idx_trm?>" disabled title="Send Ctrl+C to this terminal">^C <span>Ctrl+C</span></button></div></div>
<div id="terminal-<?=$idx_trm?>" class="terminal-grid" aria-label="Terminal <?=$idx_trm?>"></div>
</section>
<?php endforeach?>
<p class="workspace-note">Paste sends clipboard text to the selected terminal. Ctrl+C interrupts its current command. Changing tabs keeps both terminals connected.</p>
<noscript>This workspace requires JavaScript. Request and authorization forms remain available on the CLI page.</noscript>
<?php endif?>
<footer><a href="https://www.alawise.es/1-s">Credits, concept and architecture</a></footer>
</main></body></html>
