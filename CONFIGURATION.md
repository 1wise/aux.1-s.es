<!-- Timestamp: 2026-10-13 | Version: 5.1.0 | Author & Credits: https://www.alawise.es/1-s -->

# Configuración central del proyecto

`fast-boot.json` conserva el nombre histórico del proyecto. Download, deploy RAM, deploy disco y generate siguen independientes; no se añade un script orquestador.

Instalar una copia canónica fuera de html y web, por ejemplo `/var/www/aux.1-s.es/fast-boot.json`. Los tres scripts leen automáticamente el JSON situado junto a ellos; si se ejecutan desde otra carpeta, pasar `--config /var/www/aux.1-s.es/fast-boot.json`. Los argumentos CLI prevalecen para pruebas.

- Rutas y catálogo: output, cache, ram_dir, url_file, light_url_file, heavy_url_file.
- URLs: base_url, pxe_url, download_url; tec.public_url.
- TEC: tec.mail_from, admin_mail, data_dir, web_dir, session_dir, config_file.
- Hosts: hosts.aux, hosts.pxe, hosts.tec; bastion.web_hosts y bastion.cli_hosts.
- TLS: tls.certificate y tls.key son rutas locales, nunca contenido de claves.
- FPM: php_profiles.fedora/debian contienen sockets y usuario web. platform elige el perfil.
- iPXE: boot.assist_timeout_seconds; 60 segundos por defecto.
- API opcional de la ISO 6: ai.enabled, ai.openai.model, ai.gemini.model, ai.timeout_seconds y ai.max_output_tokens. Las claves se piden sin eco dentro del Live; no se guardan en este JSON público. Ver iso-assist/AI-ASSIST.md.
- FTP: ftp_host, ftp_user, ftp_port, ftp_root, ftp_tls. La contraseña se solicita de forma privada y no va en JSON.

Editar el JSON y volver a generar produce las páginas, el selector de Bastion y los ejemplos Nginx/FPM coherentes. Instalar los ejemplos descargables generados, validar Nginx/FPM y recargar los servicios. Generate no cambia servicios ni DNS. Los scripts y JSON originales permanecen revisables.

En el pool TEC usar `env[AUX_ASSIST_CONFIG] = /var/www/aux.1-s.es/fast-boot.json`. Los env AUX_ASSIST_MAIL_FROM, AUX_ASSIST_PUBLIC_URL, AUX_ASSIST_DATA_DIR y AUX_ASSIST_ADMIN_MAIL siguen admitidos por compatibilidad y prevalecen si están definidos: retirar valores antiguos para usar el JSON como fuente canónica. El usuario tec necesita lectura del JSON; mantenerlo sin secretos y fuera de los directorios públicos. Sesiones y sendmail_path se renderizan en el ejemplo del pool; cambios de pool requieren reinicio FPM. Los ajustes SMTP de Postfix y su secreto SASL siguen en /etc/postfix, no en el proyecto web.

## Bastion: b visual y p terminal

Configurar p.1-s.es y p.1-s.eu en DNS y en Multisitio OVH con el mismo directorio raíz que b.1-s.es/.eu. El índice predeterminado debe ser index.php. El index.php generado compara HTTP_HOST con bastion.cli_hosts y sirve el archivo local cli.html para p; b conserva la vista AUX. No se redirige al servidor PXE: es la réplica alojada en Bastion. Activar un certificado que cubra los nuevos nombres en el alojamiento compartido. El certificado local ntp1.1-s.eu de Excalibur no se copia al alojamiento compartido.

Después, desplegar FTP de forma independiente. No se ha creado DNS ni modificado Multisitio desde esta publicación.

usb/build.sh deriva menu.ipxe de pxe_url y lee jobs del JSON; --config permite seleccionar la copia canónica. El binario USB publicado mantiene sus metadatos anteriores hasta una compilación nueva.

Los parámetros de clonación, particionado USB/SSD y la próxima ISO se definirán en su herramienta de construcción: no se incluyen campos de configuración que todavía no tienen efecto.
