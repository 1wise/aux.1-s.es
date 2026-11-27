# Descargas: resolución previa, Gentoo fechado y firmas de Arch

Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
Author & Credits: https://www.alawise.es/1-s

La orden download comprueba primero los alias cambiantes, las referencias sin integridad fijada y las actualizaciones solicitadas que permiten resolver mediante C. Las imágenes de versión fija con hash conocido conservan su versión. Actualiza sus metadatos oficiales y conserva la política y el ID. Después transfiere y verifica los bytes. Los recursos con caché completa y hash correcto pueden reutilizarse sin red; una política fijada sin permiso de resolución se conserva. --dry-run no consulta ni descarga.

Debian Testing publica una URL que cambia de contenido. El SHA-256 se resuelve antes de una transferencia nueva; una copia con hash incorrecto nunca se publica. El catálogo incluido fija los metadatos comprobados el 23/11/2026.

Gentoo minimal utiliza el manifiesto oficial latest de autobuilds y publica la URL del directorio fechado, evitando que un cambio del enlace current borre la imagen anunciada. Se admiten tanto los manifiestos antiguos sin directorio como los nuevos con fecha/nombre. También se corrigen las configuraciones que siguen usando el índice current antiguo.

Arch netboot publica firmas PGP, no un manifiesto SHA256SUMS para estos ejecutables. AUX verifica la firma con GnuPG y la clave pública cuyo fingerprint está fijado en config/trust. Sólo entonces calcula y fija un SHA-256 local, marcado como computed-after-pgp-verification. No se presenta como checksum oficial. Se usa un keyring temporal; no se cambia el del usuario ni se importan claves desconocidas. Si falta gpg, el mensaje indica el paquete requerido.

La reanudación toma ETag/Last-Modified de la respuesta final. Una descarga parcial ya completa y válida se recupera sin red. Si el espejo rechaza la reanudación se reinicia una vez desde cero. Los errores incluyen el código de curl y HTTP. Un fallo de integridad no se convierte en éxito.

Verificación con datos reales: Debian Testing (977.272.832 bytes), Gentoo minimal (1.051.629.568 bytes) y las tres variantes Arch netboot. Se ejecutó la orden download partiendo del SHA antiguo de Debian, la URL Gentoo caducada y Arch sin SHA; las tres descargas terminaron con hashes correctos. Se rechazó una copia Arch alterada. No se certifica arranque hasta login.
