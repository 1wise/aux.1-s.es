# Public trust material

Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
Author & Credits: https://www.alawise.es/1-s

arch-netboot.asc is a public OpenPGP certificate, not a credential. Primary fingerprint: 991F6E3F0765CF6295888586139B09DA5BF0D338 (David Runge / Arch Linux). Its membership was checked against the Arch keyring maintained by the project:
https://github.com/archlinux/archlinux-keyring/tree/master/keyring/packager/dvzrv/991F6E3F0765CF6295888586139B09DA5BF0D338

Certificate retrieved on 2026-11-23 from https://keys.openpgp.org/vks/v1/by-fingerprint/991F6E3F0765CF6295888586139B09DA5BF0D338 . Payload and detached signatures come from https://archlinux.org/releng/netboot/ . AUX checks the primary fingerprint in GnuPG's VALIDSIG result. It uses a temporary keyring, without modifying the user's keyring or importing arbitrary keys from a signature.

A locally computed SHA-256 after successful signature verification is labelled as such. It is not an official SHA256SUMS sidecar and does not certify an installer login. A changed signer requires reviewing and updating the bundled trust material.
