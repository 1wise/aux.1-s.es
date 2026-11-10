# AUX application conventions

Timestamp: 2026-11-10 | Version: 7.0.0-beta.0
Author & Credits: https://www.alawise.es/1-s

- Implement terminal configuration applications with an indigo background.
- Use a cyan background for installation and generation applications.
- Show the specific application name in the header, not only the AUX suite name.
- Implement menuconfig-style interfaces behind --interactive. Preserve the CLI.
- Reuse auxlib/console_ui.py for themes, menus, checklists, fields and plan review.
- Keep keyboard navigation, selected items and a monochrome fallback usable.
- Keep ISO preparation first and installation on the current OS last in Setup.
- Show and confirm the concrete plan before installations or image builds.
- A Live recipe is not a compiled ISO. Firmware and hardware acceptance require real tests.
- Scripts and modules include Timestamp, Version and Author & Credits: https://www.alawise.es/1-s.
- Write code comments in US English.
