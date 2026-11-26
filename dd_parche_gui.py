#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interfaz gráfica para Parche Maestro ES (Darkest Dungeon)."""

import os
import queue
import re
import shutil
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import dd_parche_espanol as motor

# Paleta estilo Darkest Dungeon (modo oscuro)
COLOR_BG = "#121215"
COLOR_PANEL = "#1b1b20"
COLOR_INPUT = "#25252c"
COLOR_BORDE = "#353540"
COLOR_TEXTO = "#ece8df"
COLOR_TENUE = "#9e998e"
COLOR_ORO = "#d4a64a"
COLOR_ROJO = "#a92424"
COLOR_ROJO_HOVER = "#c42f2f"
COLOR_VERDE = "#4cc970"
COLOR_AVISO = "#e6a23c"
COLOR_ERROR = "#f05a5a"


def recurso_ruta(nombre):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nombre)


class EscritorCola:
    """Redirige los print() del motor hacia la cola de la interfaz."""

    def __init__(self, cola):
        self.cola = cola
        self._buf = ""

    def write(self, texto):
        if not texto:
            return
        self._buf += texto
        while "\n" in self._buf:
            linea, self._buf = self._buf.split("\n", 1)
            self.cola.put(("linea", linea.rstrip("\r")))

    def flush(self):
        if self._buf:
            self.cola.put(("linea", self._buf.rstrip("\r")))
            self._buf = ""

    def isatty(self):
        return False


class AplicacionParche(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Parche Maestro ES — Darkest Dungeon")
        self.geometry("760x640")
        self.minsize(700, 580)
        self.configure(bg=COLOR_BG)

        self.cola = queue.Queue()
        self.en_ejecucion = False
        self.logo_img = None
        self.mods_cache_count = 0

        self._cargar_iconos()
        self._configurar_estilos()
        self._construir_ui()
        self._autodetectar_rutas()

        self.after(80, self._procesar_cola)

    def _cargar_iconos(self):
        ruta_ico = recurso_ruta("logo.ico")
        if os.path.isfile(ruta_ico):
            try:
                self.iconbitmap(ruta_ico)
            except Exception:
                pass
        ruta_png = recurso_ruta("logo_gui.png")
        if os.path.isfile(ruta_png):
            try:
                self.logo_img = tk.PhotoImage(file=ruta_png)
            except Exception:
                self.logo_img = None

    def _configurar_estilos(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Oro.Horizontal.TProgressbar",
            troughcolor=COLOR_INPUT,
            bordercolor=COLOR_BORDE,
            background=COLOR_ORO,
            lightcolor=COLOR_ORO,
            darkcolor=COLOR_ORO,
            thickness=16,
        )

    def _construir_ui(self):
        # ===== Encabezado con logo =====
        header = tk.Frame(self, bg=COLOR_PANEL, highlightbackground=COLOR_BORDE, highlightthickness=1)
        header.pack(fill="x", padx=16, pady=(14, 10))

        inner_h = tk.Frame(header, bg=COLOR_PANEL)
        inner_h.pack(fill="x", padx=14, pady=10)

        if self.logo_img is not None:
            tk.Label(inner_h, image=self.logo_img, bg=COLOR_PANEL).pack(side="left", padx=(0, 14))

        titulos = tk.Frame(inner_h, bg=COLOR_PANEL)
        titulos.pack(side="left", fill="both", expand=True)

        tk.Label(
            titulos,
            text="PARCHE MAESTRO ESPAÑOL",
            font=("Segoe UI", 16, "bold"),
            fg=COLOR_ORO,
            bg=COLOR_PANEL,
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            titulos,
            text="Traduce tus mods de Darkest Dungeon, elimina códigos azules, parpadeos y cierres por tooltips.",
            font=("Segoe UI", 9),
            fg=COLOR_TENUE,
            bg=COLOR_PANEL,
            anchor="w",
            wraplength=560,
            justify="left",
        ).pack(fill="x", pady=(2, 0))

        # ===== Sección de rutas =====
        rutas_card = tk.Frame(self, bg=COLOR_PANEL, highlightbackground=COLOR_BORDE, highlightthickness=1)
        rutas_card.pack(fill="x", padx=16, pady=(0, 10))

        tk.Label(
            rutas_card,
            text="1. Verifica las carpetas de tu juego y mods",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_ORO,
            bg=COLOR_PANEL,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 6))

        self.var_dd = tk.StringVar()
        self.var_ws = tk.StringVar()
        self.var_dd.trace_add("write", lambda *_: self._validar_rutas_ui())
        self.var_ws.trace_add("write", lambda *_: self._validar_rutas_ui())

        self.lbl_estado_dd = self._crear_fila_ruta(
            rutas_card, "Carpeta de Darkest Dungeon:", self.var_dd, self._elegir_dd
        )
        self.lbl_estado_ws = self._crear_fila_ruta(
            rutas_card, "Carpeta de Mods (Workshop 262060):", self.var_ws, self._elegir_ws
        )

        # ===== Opciones y botones =====
        ctrl_card = tk.Frame(self, bg=COLOR_PANEL, highlightbackground=COLOR_BORDE, highlightthickness=1)
        ctrl_card.pack(fill="x", padx=16, pady=(0, 10))

        opts = tk.Frame(ctrl_card, bg=COLOR_PANEL)
        opts.pack(fill="x", padx=14, pady=(10, 6))

        self.var_solo_recompilar = tk.BooleanVar(value=False)
        self.var_retraducir = tk.BooleanVar(value=False)

        self.chk_recompilar = tk.Checkbutton(
            opts,
            text="Solo reparar tooltips y recompilar (no traduce mods nuevos)",
            variable=self.var_solo_recompilar,
            command=self._toggle_opciones,
            bg=COLOR_PANEL,
            fg=COLOR_TEXTO,
            selectcolor=COLOR_INPUT,
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_TEXTO,
            font=("Segoe UI", 9),
        )
        self.chk_recompilar.pack(anchor="w")

        self.chk_retraducir = tk.Checkbutton(
            opts,
            text="Reconstruir todos los textos desde Workshop (mantiene caché ya traducida)",
            variable=self.var_retraducir,
            command=self._toggle_opciones,
            bg=COLOR_PANEL,
            fg=COLOR_TEXTO,
            selectcolor=COLOR_INPUT,
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_TEXTO,
            font=("Segoe UI", 9),
        )
        self.chk_retraducir.pack(anchor="w", pady=(2, 0))

        btns = tk.Frame(ctrl_card, bg=COLOR_PANEL)
        btns.pack(fill="x", padx=14, pady=(6, 12))

        self.btn_iniciar = tk.Button(
            btns,
            text="▶   Generar / Actualizar Parche",
            command=self._iniciar_proceso,
            bg=COLOR_ROJO,
            fg="#ffffff",
            activebackground=COLOR_ROJO_HOVER,
            activeforeground="#ffffff",
            disabledforeground="#a8a0a0",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
        )
        self.btn_iniciar.pack(side="left")

        self.btn_abrir_mod = tk.Button(
            btns,
            text="Abrir carpeta del mod",
            command=self._abrir_carpeta_mod,
            bg=COLOR_INPUT,
            fg=COLOR_TEXTO,
            activebackground=COLOR_BORDE,
            activeforeground=COLOR_TEXTO,
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
        )
        self.btn_abrir_mod.pack(side="right")

        # ===== Progreso y consola visual =====
        prog_card = tk.Frame(self, bg=COLOR_PANEL, highlightbackground=COLOR_BORDE, highlightthickness=1)
        prog_card.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        top_prog = tk.Frame(prog_card, bg=COLOR_PANEL)
        top_prog.pack(fill="x", padx=14, pady=(10, 4))

        self.lbl_paso = tk.Label(
            top_prog,
            text="Listo para comenzar. Revisa las rutas y presiona «Generar / Actualizar Parche».",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXTO,
            bg=COLOR_PANEL,
            anchor="w",
        )
        self.lbl_paso.pack(side="left", fill="x", expand=True)

        self.lbl_pct = tk.Label(
            top_prog,
            text="0%",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_ORO,
            bg=COLOR_PANEL,
        )
        self.lbl_pct.pack(side="right")

        self.progreso = ttk.Progressbar(
            prog_card,
            style="Oro.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.progreso.pack(fill="x", padx=14, pady=(0, 10))

        # Consola amigable con colores
        log_frame = tk.Frame(prog_card, bg=COLOR_BG, highlightbackground=COLOR_BORDE, highlightthickness=1)
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        scroll = ttk.Scrollbar(log_frame)
        scroll.pack(side="right", fill="y")

        self.txt_log = tk.Text(
            log_frame,
            bg=COLOR_BG,
            fg=COLOR_TEXTO,
            font=("Segoe UI", 9),
            relief="flat",
            wrap="word",
            state="disabled",
            padx=10,
            pady=8,
            yscrollcommand=scroll.set,
        )
        self.txt_log.pack(fill="both", expand=True)
        scroll.config(command=self.txt_log.yview)

        self.txt_log.tag_configure("paso", foreground=COLOR_ORO, font=("Segoe UI", 9, "bold"))
        self.txt_log.tag_configure("ok", foreground=COLOR_VERDE, font=("Segoe UI", 9, "bold"))
        self.txt_log.tag_configure("aviso", foreground=COLOR_AVISO)
        self.txt_log.tag_configure("error", foreground=COLOR_ERROR, font=("Segoe UI", 9, "bold"))
        self.txt_log.tag_configure("tenue", foreground=COLOR_TENUE)

        self._agregar_log(
            "Bienvenido. Esta herramienta traduce y repara automáticamente tus mods en un único parche.",
            "tenue",
        )
        self._agregar_log(
            "Antes de iniciar, asegúrate de tener Darkest Dungeon completamente cerrado.",
            "aviso",
        )

    def _crear_fila_ruta(self, padre, etiqueta, variable, comando):
        bloque = tk.Frame(padre, bg=COLOR_PANEL)
        bloque.pack(fill="x", padx=14, pady=(0, 8))

        cab = tk.Frame(bloque, bg=COLOR_PANEL)
        cab.pack(fill="x")
        tk.Label(cab, text=etiqueta, font=("Segoe UI", 9), fg=COLOR_TEXTO, bg=COLOR_PANEL).pack(side="left")
        lbl_estado = tk.Label(cab, text="", font=("Segoe UI", 8, "bold"), bg=COLOR_PANEL)
        lbl_estado.pack(side="right")

        fila = tk.Frame(bloque, bg=COLOR_PANEL)
        fila.pack(fill="x", pady=(3, 0))

        entry = tk.Entry(
            fila,
            textvariable=variable,
            bg=COLOR_INPUT,
            fg=COLOR_TEXTO,
            insertbackground=COLOR_TEXTO,
            relief="flat",
            font=("Segoe UI", 9),
        )
        entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        tk.Button(
            fila,
            text="Examinar...",
            command=comando,
            bg=COLOR_BORDE,
            fg=COLOR_TEXTO,
            activebackground="#474757",
            activeforeground=COLOR_TEXTO,
            relief="flat",
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side="right")

        return lbl_estado

    def _toggle_opciones(self):
        if self.var_solo_recompilar.get() and self.var_retraducir.get():
            self.var_retraducir.set(False)

    def _autodetectar_rutas(self):
        bibliotecas = motor.obtener_bibliotecas_steam()
        for b in bibliotecas:
            cand_dd = os.path.join(b, "steamapps", "common", "DarkestDungeon")
            if not self.var_dd.get() and os.path.isfile(
                os.path.join(cand_dd, "_windows", "win32", "localization.exe")
            ):
                self.var_dd.set(cand_dd)
            cand_ws = os.path.join(b, "steamapps", "workshop", "content", "262060")
            if not self.var_ws.get() and os.path.isdir(cand_ws):
                self.var_ws.set(cand_ws)
        self._validar_rutas_ui()

    def _validar_rutas_ui(self):
        dd = self.var_dd.get().strip()
        ws = self.var_ws.get().strip()

        if dd and os.path.isfile(os.path.join(dd, "_windows", "win32", "localization.exe")):
            self.lbl_estado_dd.config(text="✔ Juego detectado", fg=COLOR_VERDE)
        else:
            self.lbl_estado_dd.config(text="⚠ Selecciona la carpeta DarkestDungeon", fg=COLOR_AVISO)

        if ws and os.path.isdir(ws):
            try:
                cant = sum(1 for d in os.listdir(ws) if os.path.isdir(os.path.join(ws, d)))
                self.lbl_estado_ws.config(text=f"✔ {cant} mods encontrados", fg=COLOR_VERDE)
            except OSError:
                self.lbl_estado_ws.config(text="⚠ Sin permisos para leer carpeta", fg=COLOR_AVISO)
        else:
            self.lbl_estado_ws.config(text="⚠ Selecciona la carpeta 262060 de Workshop", fg=COLOR_AVISO)

    def _elegir_dd(self):
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta principal de DarkestDungeon")
        if carpeta:
            self.var_dd.set(os.path.normpath(carpeta))

    def _elegir_ws(self):
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta de mods (workshop\\content\\262060)")
        if carpeta:
            self.var_ws.set(os.path.normpath(carpeta))

    def _abrir_carpeta_mod(self):
        dd = self.var_dd.get().strip()
        ruta_mod = os.path.join(dd, "mods", motor.NOMBRE_CARPETA_MOD)
        if os.path.isdir(ruta_mod):
            os.startfile(ruta_mod)
        else:
            messagebox.showinfo(
                "Parche aún no creado",
                "Todavía no existe la carpeta Parche_Maestro_ES. Ejecuta primero «Generar / Actualizar Parche».",
            )

    def _agregar_log(self, texto, tag=None):
        self.txt_log.config(state="normal")
        if tag:
            self.txt_log.insert("end", texto + "\n", tag)
        else:
            self.txt_log.insert("end", texto + "\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def _set_progreso(self, valor, texto_estado=None):
        v = max(0, min(100, int(valor)))
        self.progreso["value"] = v
        self.lbl_pct.config(text=f"{v}%")
        if texto_estado is not None:
            self.lbl_paso.config(text=texto_estado)

    def _iniciar_proceso(self):
        if self.en_ejecucion:
            return

        dd = self.var_dd.get().strip()
        ws = self.var_ws.get().strip()

        if not os.path.isfile(os.path.join(dd, "_windows", "win32", "localization.exe")):
            messagebox.showerror(
                "Carpeta del juego inválida",
                "No se encontró localization.exe dentro de la carpeta seleccionada.\n"
                "Selecciona la carpeta principal «DarkestDungeon».",
            )
            return

        if not os.path.isdir(ws):
            messagebox.showerror(
                "Carpeta de mods inválida",
                "La carpeta de Steam Workshop (262060) no existe. Selecciónala con «Examinar...».",
            )
            return

        if motor.darkest_esta_abierto():
            messagebox.showwarning(
                "Darkest Dungeon está abierto",
                "Cierra Darkest Dungeon por completo antes de generar el parche para evitar bloqueos de archivos.",
            )
            return

        self.en_ejecucion = True
        self.mods_cache_count = 0
        self.btn_iniciar.config(state="disabled", text="Trabajando...")
        self.chk_recompilar.config(state="disabled")
        self.chk_retraducir.config(state="disabled")
        self._set_progreso(2, "Preparando entorno...")
        self._agregar_log("\n──────── Iniciando proceso ────────", "paso")

        args_motor = ["dd_parche_espanol.py", "--dd", dd, "--workshop", ws]
        if self.var_solo_recompilar.get():
            args_motor.append("--solo-recompilar")
        elif self.var_retraducir.get():
            args_motor.append("--retraducir")

        hilo = threading.Thread(target=self._worker_motor, args=(args_motor, dd), daemon=True)
        hilo.start()

    def _worker_motor(self, args_motor, ruta_dd):
        argv_orig = sys.argv[:]
        out_orig, err_orig = sys.stdout, sys.stderr
        escritor = EscritorCola(self.cola)
        exito = False
        error_msg = None

        try:
            sys.argv = args_motor
            sys.stdout = escritor
            sys.stderr = escritor
            motor.main()
            # Copiar logo del mod como preview_icon.png
            src_preview = recurso_ruta("preview_icon.png")
            dst_preview = os.path.join(ruta_dd, "mods", motor.NOMBRE_CARPETA_MOD, "preview_icon.png")
            if os.path.isfile(src_preview) and os.path.isdir(os.path.dirname(dst_preview)):
                shutil.copy2(src_preview, dst_preview)
            exito = True
        except SystemExit as e:
            if e.code in (0, None):
                exito = True
            else:
                error_msg = "El proceso se detuvo. Revisa el registro de arriba para ver el detalle."
        except Exception as e:
            error_msg = f"Ocurrió un error inesperado: {e}"
        finally:
            escritor.flush()
            sys.argv = argv_orig
            sys.stdout = out_orig
            sys.stderr = err_orig
            self.cola.put(("fin", (exito, error_msg)))

    def _formatear_y_mostrar_linea(self, linea):
        l = linea.strip()
        if not l:
            return

        # Paso 1 a 5
        if l.startswith("1/5 "):
            self._set_progreso(6, "Paso 1/5 — Protegiendo textos originales del juego...")
            self._agregar_log("① Protegiendo el español original del juego base y los DLCs...", "paso")
            return
        if l.startswith("2/5 "):
            self._set_progreso(14, "Paso 2/5 — Escaneando tus mods instalados...")
            self._agregar_log("② Analizando mods de Steam Workshop...", "paso")
            return
        if l.startswith("3/5 "):
            if "omitida" in l.lower():
                self._set_progreso(70, "Paso 3/5 — Traducciones ya listas en caché.")
                self._agregar_log("③ Sin traducciones pendientes (usando archivos existentes).", "paso")
            else:
                self._set_progreso(20, "Paso 3/5 — Traduciendo mods pendientes...")
                self._agregar_log("③ Traduciendo mods que faltan al español...", "paso")
            return
        if l.startswith("4/5 "):
            if self.mods_cache_count > 0:
                self._agregar_log(f"   ✔ {self.mods_cache_count} mods cargados al instante desde caché previa.", "tenue")
                self.mods_cache_count = 0
            self._set_progreso(72, "Paso 4/5 — Revisando tooltips anti-crasheo...")
            self._agregar_log("④ Revisando porcentajes y etiquetas de color para evitar cierres...", "paso")
            return
        if l.startswith("5/5 "):
            self._set_progreso(76, "Paso 5/5 — Compilando archivos del parche...")
            self._agregar_log("⑤ Compilando los archivos finales del parche (.loc2)...", "paso")
            return

        # Progreso individual de traducciones: [15/170] 1133384392 -> ...
        m_trad = re.match(r"^\[(\d+)/(\d+)\]\s+(\S+)\s+->\s+(.+)$", l)
        if m_trad:
            hechos, total, mod_id, detalle = int(m_trad.group(1)), int(m_trad.group(2)), m_trad.group(3), m_trad.group(4)
            pct = 20 + int((hechos / max(total, 1)) * 50)
            self._set_progreso(pct, f"Paso 3/5 — Procesando mods ({hechos}/{total})...")
            if "cargado desde XML previo" in detalle:
                self.mods_cache_count += 1
            else:
                self._agregar_log(f"   • Mod {mod_id}: {detalle}", "tenue")
            return

        # Progreso de compilación: Overrides compilados: [40/146] (...)
        m_comp = re.match(r"^Overrides compilados:\s+\[(\d+)/(\d+)\]", l)
        if m_comp:
            hechos, total = int(m_comp.group(1)), int(m_comp.group(2))
            pct = 76 + int((hechos / max(total, 1)) * 20)
            self._set_progreso(pct, f"Paso 5/5 — Compilando overrides ({hechos}/{total})...")
            self._agregar_log(f"   • Compilados {hechos} de {total} paquetes de idioma...", "tenue")
            return

        # Resumen amigable y avisos
        if "RESUMEN FINAL" in l:
            self._set_progreso(100, "¡Parche listo! Actívalo en el puesto #1 dentro del juego.")
            self._agregar_log("\n✔ ¡PARCНE GENERADO CON ÉXITO!".replace("Н", "H"), "ok")
            return
        if l.startswith("[ERROR]"):
            self._agregar_log("✖ " + l.replace("[ERROR]", "").strip(), "error")
            return
        if l.startswith("[PAUSA 429]") or l.startswith("[AVISO]"):
            self._agregar_log("⚠ " + l, "aviso")
            return
        if any(
            l.startswith(p)
            for p in (
                "Caché cargada:",
                "Mods analizados:",
                "Mods con español falso",
                "Mods solo-.loc2",
                "Entradas saneadas:",
                "Mod generado en",
                "Overrides compilados (español falso):",
                "Duplicados bloqueados",
                "Total de .loc2 instalados:",
                "Siguiente paso:",
                "y colócalo",
            )
        ):
            self._agregar_log("   " + l)

    def _procesar_cola(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "linea":
                    self._formatear_y_mostrar_linea(dato)
                elif tipo == "fin":
                    exito, err = dato
                    self.en_ejecucion = False
                    self.btn_iniciar.config(state="normal", text="▶   Generar / Actualizar Parche")
                    self.chk_recompilar.config(state="normal")
                    self.chk_retraducir.config(state="normal")
                    if exito:
                        messagebox.showinfo(
                            "Parche listo",
                            "¡Todo quedó compilado y reparado!\n\n"
                            "Abre Darkest Dungeon, entra al martillo azul de tu partida, "
                            "activa «Parche Maestro Traduccion Espanol» y súbelo al puesto #1.",
                        )
                    else:
                        self._set_progreso(0, "Proceso interrumpido.")
                        if err:
                            self._agregar_log("✖ " + err, "error")
                        messagebox.showerror("No se pudo completar", err or "Revisa el registro.")
        except queue.Empty:
            pass
        self.after(80, self._procesar_cola)


if __name__ == "__main__":
    app = AplicacionParche()
    app.mainloop()