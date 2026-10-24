# AUX / PXE / TEC · aplicar 5.0.2 en Excalibur

Timestamp: 2026-10-12 | Version: 5.0.2
Author & Credits: https://www.alawise.es/1-s

La web publicada distribuye código y una llave nueva. No modifica automáticamente
DNS, certificados, servicios o ficheros de Excalibur.

| Servicio | Nombres .es / .eu | Raíz pública |
| --- | --- | --- |
| AUX | aux.1-s.es / aux.1-s.eu | /var/www/aux.1-s.es/html |
| PXE | pxe.1-s.es / pxe.1-s.eu | /var/www/aux.1-s.es/html, índice cli.html |
| TEC | tec.1-s.es / tec.1-s.eu | /var/www/aux.1-s.es/web |

Cache persistente: `/var/www/aux.1-s.es/isos`. JSON privado existente:
`/var/lib/aux-assist`. Conservarlo y respaldarlo antes de cambiar su propietario
al usuario del pool TEC. No moverlo a html/, web/ ni a la réplica FTP.

1. Crear DNS de los dos nombres TEC hacia Excalibur. Respaldar los vhosts, el
   pool, los JSON y la web actual. El pool nuevo conserva AUX_ASSIST_*.
2. Descomprimir `tec-platform-5.0.2.zip` en `/var/www/aux.1-s.es/`. Seguir README.md
   para usuario `tec`, permisos, contextos SELinux y pool `/run/php-fpm/tec.sock`.
   El pool www de AUX permanece separado. No hacer chown recursivo de /var/www.
3. Configurar la cuenta OVH `tec@1wise.es` siguiendo MAIL.md. Actualizar el relay,
   credenciales SASL y posibles reescrituras del remitente antiguo. La contraseña
   se introduce solo en `/etc/postfix/sasl_passwd`, nunca en una web o ZIP.
4. Disponer de un certificado SAN que cubra los seis nombres de la tabla. El
   ejemplo actual espera `/etc/letsencrypt/live/ntp1.1-s.eu/{fullchain,privkey}.pem`; adaptar
   esas dos rutas si el certificado tiene otro nombre. Instalar nginx.conf.example
   como `/etc/nginx/conf.d/aux-pxe-tec.conf`, reemplazando los vhosts anteriores
   que definan esos nombres. `nginx -t` debe pasar antes de la recarga.
5. Descomprimir `aux-pxe-5.0.2.zip` en el directorio de trabajo de los tres
   comandos. Si conservas un fast-boot.json propio, actualizar expresamente
   output a `/var/www/aux.1-s.es/html` y cache a `/var/www/aux.1-s.es/isos`.
   Las actualizaciones conservan tu configuración existente.
   Si el cache todavía está en aux.1-s.eu/isos, trasladar su contenido al nuevo
   directorio conservando los metadatos y volver a ejecutar deploy para actualizar
   sus enlaces. Reutilizar las descargas completas antes de descargar de nuevo.
6. Ejecutar las fases por separado, solo las que correspondan:

```bash
# Descargar únicamente si necesitas renovar el cache.
sudo bash download.sh --verbose

# Elegir RAM o disco; deploy no llama a download ni a generate.
sudo bash deploy.sh ram --verbose
# Alternativa persistente: sudo bash deploy.sh disk --verbose

# Rastrear las unidades realmente desplegadas.
sudo bash generate.sh --verbose
```

7. Validar servicios y HTTP, conservando el HTTP de PXE:

```bash
sudo php-fpm -t
sudo nginx -t
sudo systemctl restart php-fpm
sudo systemctl reload nginx
curl -I https://aux.1-s.es/assets/portal.css
curl -I http://pxe.1-s.es/menu.ipxe
curl -I https://tec.1-s.es/
```

CSS debe ser text/css y menu.ipxe text/plain. Probar también los alias .eu,
el catálogo PXE con Links, browse contents y una descarga reanudable.
Probar el formulario TEC y su confirmación de correo; reenviar los enlaces
pendientes para sustituir el dominio anterior. Retirar el vhost TECH anterior
tras comprobar el nuevo servicio.

## Asistencia y llave

Las ISOs de asistencia aparecen en **0. Remote assistance**, antes de Distros
y Tools. Generar después de desplegar cada ISO. Las versiones se ordenan por
números, con la final por delante de sus dev. La detección de aux.assist y los
archivos reales deciden si existe una receta arrancable. iPXE espera 60 segundos
y arranca la versión más reciente compatible; cualquier tecla detiene la cuenta.
Sin una ISO compatible desplegada no hay arranque automático. Entrar al Live no
abre SSH: el cliente debe autorizar al técnico dentro de la ISO.

`usb/aux-ipxe-usb.img` ahora incluye GRUB con menú visible y 5 segundos, seguido
de iPXE y DHCP hacia `http://pxe.1-s.es/menu.ipxe`. Hay que volver a grabar las
llaves anteriores para obtener GRUB. Consultar usb/README.md antes de usar dd.
La imagen UEFI es unsigned; las pruebas de VM usan Secure Boot desactivado.

Las fuentes `tec-fedora44-rescue-5.0.1-dev.5-sources.zip` usan perfiles públicos
en `https://tec.1-s.es/profiles.php`. Su README incluye el comando de compilación
y los 94 paquetes solicitados, con Wi-Fi. Ese ZIP no contiene una ISO Linux
compilada: construirla en Fedora, probarla y luego desplegarla en Excalibur.
