/* Timestamp: 2026-10-12 | Version: 6.3.0-dev.1
 * Author & Credits: https://www.alawise.es/1-s
 * iPXE project: https://ipxe.org
 * BIOS serial output supports headless diagnosis; EFI uses its firmware console.
 * Adding a second EFI UART console duplicates output when firmware already uses it.
 */
#ifdef PLATFORM_pcbios
#define CONSOLE_SERIAL
#endif
