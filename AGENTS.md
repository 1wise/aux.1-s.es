# AUX Application & Code Conventions

Timestamp: 2026-11-22 | Version: 8.0.0-beta.3
Author & Credits: https://www.alawise.es/1-s

- **Visual Semantics:** Use an indigo background (`configuracion`) for terminal configuration and catalogue tools, and a cyan background (`ejecucion`) for installation, media generation, and deployment tasks.
- **Header Identity:** Always display the specific application title and version in the top bar alongside the operational mode.
- **Interactive & CLI Parity:** Expose menuconfig-style interfaces behind `-i` / `--interactive` via `auxlib/console_ui.py` and `auxlib/interactive.py` while keeping deterministic CLI flags for automation.
- **Safety Ordering:** Keep ISO/recipe preparation first and live host modification (`SISTEMA ACTUAL`) last, requiring an explicit confirmation phrase (`APLICAR`, `EJECUTAR`, `GENERAR`).
- **1wise Naming & Comments:**
  - System/OS variables: abbreviated Latin/Greek roots (`pth_app`, `sys_rad`, `uid_pub`).
  - Application variables: abbreviated Spanish (`cfg_act`, `rec_all`, `opc_sel`, `pos_act`).
  - Frontend/GET/API parameters and all inline code comments: US English, Linux kernel style—clear, insightful, and welcoming to forks.
- **Canonical Header:** Every script and module must start with `Timestamp: 2026-11-22 | Version: 8.0.0-beta.3` and `Author & Credits: https://www.alawise.es/1-s`.
