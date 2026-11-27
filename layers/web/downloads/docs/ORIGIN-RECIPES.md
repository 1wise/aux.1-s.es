# Windows y macOS desde el menú iPXE

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
Author & Credits: https://www.alawise.es/1-s

Las once fichas de la propuesta v8.2 usan la política de origen 004. La adquisición del medio se realiza en el portal correspondiente. Los números de compilación son los declarados en el documento. El selector conserva por separado la evidencia de descarga, despliegue y arranque hasta el login.

Al generar la web, AUX añade sub_win.ipxe y sub_mac.ipxe al lado de menu.ipxe si el catálogo activo contiene perfiles de la rama. El libro de recetas enlaza a los mismos archivos. Cada grupo prepara los medios que desea ofrecer desde su servidor.

## Windows y WinPE

Desde la raíz HTTP que sirve los scripts, colocar el binario del proyecto iPXE en media/windows/bin/wimboot para x86 y en media/windows/bin/wimboot.arm64 para ARM64. Preparar media/windows/<perfil>/<arquitectura>/sources/boot.wim con el ADK y el complemento WinPE o con el medio oficial de la edición. Las carpetas de arquitectura son x86_64 y arm64.

Perfiles: win11-26h2-x64, win11-26h2-arm64, win11-24h2-ltsc, win10-21h2-iot-ltsc, winserv-2025 y winpe-11-adk.

Para instalación, comprobar que el índice 2 de boot.wim corresponde a Windows Setup. La plantilla inyecta pxe/winpeshl.ini y pxe/install.bat desde la misma carpeta de arquitectura. Preparar ambos archivos para que el entorno WinPE inicialice la red y ejecute el instalador desde el recurso SMB del grupo. Las credenciales, si son necesarias, se solicitan en WinPE. Para WinPE independiente se usa el índice 1 sin inyectar esos archivos. Preparar el controlador de red que necesite el cliente.

Ejemplo de comprobación de la disposición de archivos para Server 2025:

    media/windows/bin/wimboot
    media/windows/winserv-2025/x86_64/sources/boot.wim
    media/windows/winserv-2025/x86_64/pxe/winpeshl.ini
    media/windows/winserv-2025/x86_64/pxe/install.bat

Para servir los medios desde otro host, fijar aux_win_root en el script de entrada antes de encadenar el submenú. Su valor es la URL base que contiene bin/ y los directorios de perfiles. La lista de opciones depende del firmware y la arquitectura del cliente.

Referencia: https://ipxe.org/wimboot

## macOS

En Mac Intel con UEFI x86_64, la receta experimental permite encadenar un árbol OpenCore preparado para ese modelo y su arranque en red. Mantener la estructura EFI, la configuración y los controladores que necesite OpenCore. Las dos opciones de recuperación requieren imágenes de disco arrancables preparadas por el operador para el modelo correspondiente. La receta utiliza estas rutas respecto a la raíz HTTP de los scripts:

    media/macos/opencore-1.0.8/EFI/OC/OpenCore.efi
    media/macos/macos-26-tahoe/tahoe-recovery-oc108.img
    media/macos/macos-15-sequoia/sequoia-recovery-oc108.img

Para cambiar de servidor, fijar aux_mac_root en el script de entrada. En Apple Silicon la ficha remite a las opciones de arranque y a Recuperación de macOS. OpenCore y Mist enlazan a sus respectivos proyectos. Las pruebas sobre hardware compatible siguen pendientes.

Recuperación de Apple: https://support.apple.com/en-us/102655

Documento de origen: https://docs.google.com/document/d/1Lj_fzO0wjBFwfUUX6eBEQOo_22RSs8F5qojEGDoiDYY
