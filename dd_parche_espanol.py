#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Parche Maestro ES - Traductor y Reparador de Mods para Darkest Dungeon
----------------------------------------------------------------------
Automatiza la traducción al español, reparación de tooltips y compilación .loc2
de todos los mods instalados en Steam Workshop en un único mod local
(Parche_Maestro_ES) listo para colocarse en la posición #1 del orden de carga.

Requisitos: Python 3.8+ en Windows (sin librerías externas).
Uso básico:
    py -3 dd_parche_espanol.py
Opciones:
    --dd "RUTA"          Ruta manual a DarkestDungeon
    --workshop "RUTA"    Ruta manual a workshop\content\262060
    --solo-recompilar    Omite traducciones nuevas; solo repara XML y recompila
    --retraducir         Regenera los XML desde Workshop (conservando caché JSON)
"""

import argparse
import glob
import html
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import winreg
except ImportError:
    winreg = None

# ================= CONFIGURACIÓN GENERAL =================
NOMBRE_CARPETA_MOD = "Parche_Maestro_ES"
TITULO_MOD = "Parche Maestro Traduccion Espanol"
ENDPOINT_TRADUCTOR = "https://clients5.google.com/translate_a/t"

MAX_WORKERS = 2
MAX_ITEMS_LOTE = 30
MAX_CHARS_LOTE = 3200
PAUSA_MINIMA_REQ = 0.45
REINTENTOS = 4
SEPARADOR_FALLBACK = "\nQSEPQ\n"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Prefijos que deben ser únicos para evitar parpadeo en tooltips y abalorios
PREFIJOS_UNICOS = (
    "buff_stat_tooltip_",
    "trinket_",
    "combat_skill_name_",
    "camping_skill_name_",
    "hero_class_name_",
    "str_inventory_title_",
    "str_inventory_description_",
    "str_inventory_set_title_",
    "upgrade_tree_name_",
    "str_quirk_name_",
    "str_quirk_description_",
    "str_skill_mode_info_",
    "effect_tooltip_",
    "str_monstername_",
    "str_curio_title_",
    "town_name_",
    "dungeon_name_",
)

# Prefijos formateados por sprintf en el motor C++ del juego
PREFIJOS_FORMATEADOS = (
    "buff_stat_tooltip_",
    "buff_rule_tooltip_",
    "effect_tooltip_",
    "trinket_",
    "str_skill_",
    "combat_skill_",
    "camping_skill_",
    "str_quirk_",
    "upgrade_",
    "actor_dot_",
    "skill_",
    "str_inventory_set_",
    "str_tooltip_",
)

PALABRAS_EN = {
    "the", "and", "with", "from", "your", "their", "this", "that", "when",
    "after", "before", "each", "gain", "gains", "cannot", "only", "target",
    "damage", "stress", "heal", "healing", "turn", "turns", "bleed", "blight",
    "stun", "move", "buff", "debuff", "enemy", "enemies", "party", "attack",
    "skill", "skills", "hit", "miss", "crit", "dodge", "prot", "speed",
    "resist", "chance", "round", "rounds", "battle", "combat", "camp",
    "trinket", "hero", "heroes", "allies", "ally", "self", "apply", "drain",
    "remove", "clear", "ignore", "stealth", "mark", "guard", "riposte",
}
PALABRAS_ES = {
    "el", "la", "los", "las", "del", "una", "con", "por", "para", "como",
    "cuando", "cada", "daño", "estrés", "curar", "curación", "turno", "turnos",
    "hemorragia", "infección", "aturdimiento", "movimiento", "enemigo",
    "enemigos", "grupo", "ataque", "habilidad", "objetivo", "evasión",
    "velocidad", "resistencia", "probabilidad", "ronda", "rondas", "combate",
    "héroe", "aliado", "aliados", "mismo", "aplica", "elimina", "ignora",
    "sigilo", "marca", "guardia", "respuesta", "crítico", "mejora", "merma",
}
# =========================================================

# ================= EXPRESIONES REGULARES =================
PATRON_COMENTARIO = re.compile(r"<!--.*?-->", flags=re.DOTALL)
PATRON_LANGUAGE = re.compile(
    r'<language\s+id=["\']([^"\']+)["\']\s*>(.*?)</language>',
    flags=re.DOTALL | re.IGNORECASE,
)
PATRON_ENTRY = re.compile(
    r'<entry\s+id=["\']([^"\']+)["\']\s*>\s*(?:<!\[CDATA\[(.*?)\]\]>|(.*?))\s*</entry>',
    flags=re.DOTALL | re.IGNORECASE,
)
PATRON_CODIGOS = re.compile(
    r"(\{[^}\r\n]+\}|%(?:%|[+\-#0]*\d*(?:\.\d+)?[diufFeEgGcsSxXo])|\\n|\\t|\r?\n)"
)
PATRON_CONTROL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
PATRON_CJK = re.compile(r"[\u4e00-\u9fff]")
PATRON_LETRAS = re.compile(r"[A-Za-z\u4e00-\u9fff]")
PATRON_PALABRAS = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")

PATRON_COLOR_TOKEN = re.compile(
    r"(\{colour_start\|[^}\r\n]+\}|\{colour_end\})", flags=re.IGNORECASE
)
PATRON_COLOR_ROTO = re.compile(
    r"\{colour_(?:start(?:\|)?|end[^}\r\n]+)\}", flags=re.IGNORECASE
)
PATRON_PCT = re.compile(
    r"(%%)"
    r"|(%[+\-#0]*\d*(?:\.\d+)?[hlL]?[diuoxXeEfFgGaAcCsSpn])"
    r"|(%[ ]+[+\-#0 ]*\d*(?:\.\d+)?[hlL]?[diuoxXeEfFgGaAcCsSpn])"
    r"|(%)"
)
PATRON_SPEC_REAL = re.compile(
    r"(%%)|(%[+\-#0]*\d*(?:\.\d+)?[hlL]?([diuoxXeEfFgGaAcCsSpn]))"
)
# =========================================================

CACHE_LOCK = threading.Lock()
CACHE = {}
RATE_LOCK = threading.Lock()
ULTIMA_REQ = 0.0


# ================= DETECCIÓN DE RUTAS ====================
def obtener_bibliotecas_steam():
    raices = []
    if winreg is not None:
        for clave_base, subclave, valor in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ):
            try:
                with winreg.OpenKey(clave_base, subclave) as k:
                    ruta, _ = winreg.QueryValueEx(k, valor)
                    if ruta and os.path.isdir(ruta):
                        raices.append(os.path.normpath(ruta))
            except OSError:
                pass

    for candidata in (
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam",
        r"D:\Steam",
        r"D:\SteamLibrary",
        r"E:\Steam",
        r"E:\SteamLibrary",
    ):
        if os.path.isdir(candidata):
            raices.append(candidata)

    bibliotecas = []
    vistas = set()

    def agregar(ruta):
        norm = os.path.normpath(ruta)
        low = norm.lower()
        if low not in vistas and os.path.isdir(norm):
            vistas.add(low)
            bibliotecas.append(norm)

    for r in raices:
        agregar(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            try:
                contenido = open(vdf, "r", encoding="utf-8", errors="ignore").read()
                for m in re.finditer(r'"path"\s+"([^"]+)"', contenido):
                    agregar(m.group(1).replace("\\\\", "\\"))
            except OSError:
                pass

    return bibliotecas


def detectar_rutas(dd_manual=None, ws_manual=None):
    ruta_dd = dd_manual
    ruta_ws = ws_manual
    bibliotecas = obtener_bibliotecas_steam()

    if not ruta_dd:
        for b in bibliotecas:
            cand = os.path.join(b, "steamapps", "common", "DarkestDungeon")
            if os.path.isfile(os.path.join(cand, "_windows", "win32", "localization.exe")):
                ruta_dd = cand
                break

    if not ruta_ws:
        for b in bibliotecas:
            cand = os.path.join(b, "steamapps", "workshop", "content", "262060")
            if os.path.isdir(cand):
                ruta_ws = cand
                break

    if not ruta_dd or not os.path.isdir(ruta_dd):
        ruta_dd = input("Ruta a la carpeta DarkestDungeon: ").strip().strip('"')
    if not ruta_ws or not os.path.isdir(ruta_ws):
        ruta_ws = input("Ruta a workshop\\content\\262060: ").strip().strip('"')

    return os.path.normpath(ruta_dd), os.path.normpath(ruta_ws)


def darkest_esta_abierto():
    if os.name != "nt":
        return False
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq Darkest.exe"],
            stderr=subprocess.DEVNULL,
            text=True,
            errors="ignore",
        )
        return "darkest.exe" in out.lower()
    except Exception:
        return False


def asegurar_project_xml(ruta_mod):
    os.makedirs(ruta_mod, exist_ok=True)
    os.makedirs(os.path.join(ruta_mod, "localization"), exist_ok=True)
    ruta_proj = os.path.join(ruta_mod, "project.xml")
    if os.path.isfile(ruta_proj):
        return
    contenido = f"""<?xml version="1.0" encoding="utf-8"?>
<project>
\t<PreviewIconFile>preview_icon.png</PreviewIconFile>
\t<ItemDescriptionShort>Traduccion y correccion automatica al espanol para tus mods.</ItemDescriptionShort>
\t<ModDataPath>{ruta_mod}</ModDataPath>
\t<Title>{TITULO_MOD}</Title>
\t<Language>spanish</Language>
\t<UpdateDetails>Generado automaticamente por dd_parche_espanol.py</UpdateDetails>
\t<Visibility>private</Visibility>
\t<UploadMode>direct_upload</UploadMode>
\t<VersionMajor>1</VersionMajor>
\t<VersionMinor>0</VersionMinor>
\t<TargetBuild>0</TargetBuild>
\t<Tags>
\t\t<Tags>Localization</Tags>
\t</Tags>
\t<ItemDescription>Parche maestro en espanol sin textos duplicados ni errores de tooltip. Colocar en la posicion #1 del orden de carga.</ItemDescription>
\t<PublishedFileId>0</PublishedFileId>
</project>
"""
    with open(ruta_proj, "w", encoding="utf-8") as f:
        f.write(contenido)


# ================= CACHÉ Y TRADUCTOR =====================
def esperar_turno():
    global ULTIMA_REQ
    with RATE_LOCK:
        ahora = time.monotonic()
        delta = ahora - ULTIMA_REQ
        objetivo = PAUSA_MINIMA_REQ + random.uniform(0.05, 0.20)
        if delta < objetivo:
            time.sleep(objetivo - delta)
        ULTIMA_REQ = time.monotonic()


def cargar_cache(archivo_cache):
    if os.path.exists(archivo_cache):
        try:
            with open(archivo_cache, "r", encoding="utf-8") as f:
                CACHE.update(json.load(f))
            print(f"Caché cargada: {len(CACHE)} textos previos.")
        except Exception as e:
            print(f"[AVISO] No se pudo leer la caché ({e}).")


def guardar_cache(archivo_cache):
    with CACHE_LOCK:
        tmp = archivo_cache + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(CACHE, f, ensure_ascii=False)
        os.replace(tmp, archivo_cache)


def extraer_texto_json(item):
    while isinstance(item, list) and item:
        item = item[0]
    return str(item).strip()


def http_traducir_post(bloque, src_lang):
    query = urllib.parse.urlencode({"client": "dict-chrome-ex", "sl": src_lang, "tl": "es"})
    url = f"{ENDPOINT_TRADUCTOR}?{query}"
    data = urllib.parse.urlencode([("q", t) for t in bloque]).encode("utf-8")
    ultimo_error = None

    for intento in range(REINTENTOS):
        esperar_turno()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                parsed = json.loads(resp.read().decode("utf-8", errors="ignore"))
                if isinstance(parsed, list) and len(parsed) == len(bloque):
                    return [extraer_texto_json(x) for x in parsed], None, 200
                return None, "Formato inesperado", 200
        except urllib.error.HTTPError as e:
            if e.code == 429:
                espera = 20 * (intento + 1)
                print(f"  [PAUSA 429] Esperando {espera}s...")
                time.sleep(espera)
                ultimo_error = "HTTP 429"
                continue
            return None, f"HTTP {e.code}", e.code
        except Exception as e:
            ultimo_error = f"{type(e).__name__}: {e}"
            time.sleep((2 ** (intento + 1)) + random.uniform(0.5, 1.5))

    return None, ultimo_error, 0


def http_traducir_get_unico(texto, src_lang):
    query = urllib.parse.urlencode(
        {"client": "dict-chrome-ex", "sl": src_lang, "tl": "es", "q": texto}
    )
    url = f"{ENDPOINT_TRADUCTOR}?{query}"
    ultimo_error = None

    for intento in range(REINTENTOS):
        esperar_turno()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                parsed = json.loads(resp.read().decode("utf-8", errors="ignore"))
                if isinstance(parsed, list) and parsed:
                    return extraer_texto_json(parsed[0]), None
                ultimo_error = "Respuesta vacía"
        except urllib.error.HTTPError as e:
            if e.code == 429:
                espera = 20 * (intento + 1)
                print(f"  [PAUSA 429] Esperando {espera}s...")
                time.sleep(espera)
                ultimo_error = "HTTP 429"
                continue
            ultimo_error = f"HTTP {e.code}"
            time.sleep(2)
        except Exception as e:
            ultimo_error = f"{type(e).__name__}: {e}"
            time.sleep((2 ** (intento + 1)) + random.uniform(0.5, 1.5))

    return None, ultimo_error


def traducir_lote_get_fallback(bloque, indices, src_lang, resultados, fallos):
    if not bloque:
        return
    if len(bloque) == 1:
        trad, _ = http_traducir_get_unico(bloque[0], src_lang)
        if trad is not None:
            resultados[indices[0]] = trad
            with CACHE_LOCK:
                CACHE[f"{src_lang}||{bloque[0]}"] = trad
        else:
            fallos.append(indices[0])
        return

    unido = SEPARADOR_FALLBACK.join(bloque)
    if len(unido) <= 1600:
        trad, err = http_traducir_get_unico(unido, src_lang)
        if trad is not None:
            partes = re.split(r"\s*QSEPQ\s*", trad, flags=re.IGNORECASE)
            if len(partes) == len(bloque):
                with CACHE_LOCK:
                    for idx, orig, p in zip(indices, bloque, partes):
                        limpio = p.strip()
                        resultados[idx] = limpio
                        CACHE[f"{src_lang}||{orig}"] = limpio
                return
        elif err and "429" in err:
            fallos.extend(indices)
            return

    mitad = len(bloque) // 2
    traducir_lote_get_fallback(bloque[:mitad], indices[:mitad], src_lang, resultados, fallos)
    traducir_lote_get_fallback(bloque[mitad:], indices[mitad:], src_lang, resultados, fallos)


def traducir_textos_por_idioma(items):
    resultados = [x[0] for x in items]
    fallos = []
    por_idioma = {}

    for i, (txt, src_lang) in enumerate(items):
        clave = f"{src_lang}||{txt}"
        with CACHE_LOCK:
            cached = CACHE.get(clave)
        if cached is not None:
            resultados[i] = cached
        else:
            por_idioma.setdefault(src_lang, []).append((i, txt))

    for src_lang, pendientes in por_idioma.items():
        bloque, indices, largo = [], [], 0

        def enviar(b, idxs):
            trads, _, status = http_traducir_post(b, src_lang)
            if trads is not None:
                with CACHE_LOCK:
                    for idx, orig, t in zip(idxs, b, trads):
                        resultados[idx] = t
                        CACHE[f"{src_lang}||{orig}"] = t
            elif status == 429:
                fallos.extend(idxs)
            else:
                traducir_lote_get_fallback(b, idxs, src_lang, resultados, fallos)

        for idx, txt in pendientes:
            if bloque and (len(bloque) >= MAX_ITEMS_LOTE or largo + len(txt) > MAX_CHARS_LOTE):
                enviar(bloque, indices)
                bloque, indices, largo = [], [], 0
            bloque.append(txt)
            indices.append(idx)
            largo += len(txt)
        if bloque:
            enviar(bloque, indices)

    return resultados, len(fallos)


# ================= PROCESAMIENTO XML =====================
def extraer_bloques_xml(ruta_archivo):
    with open(ruta_archivo, "r", encoding="utf-8-sig", errors="ignore") as f:
        contenido = f.read()
    contenido = PATRON_COMENTARIO.sub("", contenido)
    bloques = {}
    for m_lang in PATRON_LANGUAGE.finditer(contenido):
        lang = m_lang.group(1).strip().lower()
        entradas = bloques.setdefault(lang, [])
        for m_ent in PATRON_ENTRY.finditer(m_lang.group(2)):
            eid = m_ent.group(1).strip()
            txt = (
                m_ent.group(2)
                if m_ent.group(2) is not None
                else html.unescape(m_ent.group(3) or "")
            )
            entradas.append((eid, PATRON_CONTROL_XML.sub("", txt)))
    return bloques


def construir_xml(entradas_es, incluir_dummy_en=False):
    lineas = ['<?xml version="1.0" encoding="UTF-8"?>', "<root>", '  <language id="spanish">']
    for eid, txt in entradas_es:
        id_seg = html.escape(eid, quote=True)
        txt_seg = PATRON_CONTROL_XML.sub("", txt).replace("]]>", "]]]]><![CDATA[>")
        lineas.append(f'    <entry id="{id_seg}"><![CDATA[{txt_seg}]]></entry>')
    lineas.append("  </language>")
    if incluir_dummy_en:
        lineas.append('  <language id="english">')
        lineas.append('    <entry id="parche_maestro_base"><![CDATA[base]]></entry>')
        lineas.append("  </language>")
    lineas.append("</root>\n")
    xml_final = "\n".join(lineas)
    ET.fromstring(xml_final.encode("utf-8"))
    return xml_final


def normalizar_cmp(texto):
    limpio = PATRON_CODIGOS.sub(" ", texto)
    return re.sub(r"\s+", " ", limpio).strip().lower()


def parece_ingles(texto):
    if PATRON_CJK.search(texto):
        return False
    sin_cod = PATRON_CODIGOS.sub(" ", texto)
    if re.search(r"[áéíóúüñ¿¡ÁÉÍÓÚÜÑ]", sin_cod):
        return False
    palabras = [w.lower() for w in PATRON_PALABRAS.findall(sin_cod)]
    if len(palabras) < 2:
        return False
    en_hits = sum(1 for w in palabras if w in PALABRAS_EN)
    es_hits = sum(1 for w in palabras if w in PALABRAS_ES)
    return en_hits >= 1 and en_hits > es_hits


def proteger_codigos(texto):
    tokens = []
    esp_ini = texto[: len(texto) - len(texto.lstrip(" \t"))]
    esp_fin = texto[len(texto.rstrip(" \t")) :]

    def reemplazar(match):
        inicio, fin = match.start(), match.end()
        esp_antes = inicio > 0 and texto[inicio - 1] in (" ", "\t")
        esp_despues = fin < len(texto) and texto[fin] in (" ", "\t")
        idx = len(tokens)
        tokens.append((match.group(0), esp_antes, esp_despues))
        return f" XQ{idx}QX "

    protegido = PATRON_CODIGOS.sub(reemplazar, texto)
    protegido = re.sub(r"[ \t]{2,}", " ", protegido).strip()
    return protegido, tokens, esp_ini, esp_fin


def restaurar_codigos(texto_trad, tokens, esp_ini, esp_fin, texto_original):
    res = texto_trad
    for i, (codigo, esp_antes, esp_despues) in enumerate(tokens):
        patron = re.compile(rf"([ \t]*)XQ\s*{i}\s*QX([ \t]*)", flags=re.IGNORECASE)
        if not patron.search(res):
            return texto_original, False

        def rep(m, c=codigo, ea=esp_antes, ed=esp_despues):
            pref = " " if (ea and m.start() > 0) else ""
            sig = m.string[m.end()] if m.end() < len(m.string) else ""
            suf = " " if (ed and sig and sig not in ".,;:!?)]}") else ""
            return f"{pref}{c}{suf}"

        res = patron.sub(rep, res, count=1)

    return f"{esp_ini}{res.strip()}{esp_fin}", True


def necesita_traduccion(texto_protegido):
    sin_tokens = re.sub(r"XQ\d+QX", "", texto_protegido)
    return bool(PATRON_LETRAS.search(sin_tokens))


def detectar_idioma_origen(texto, idioma_bloque):
    if PATRON_CJK.search(texto):
        return "zh-TW" if idioma_bloque == "tchinese" else "zh-CN"
    return "en"


# ================= SANEADORES ANTI-CRASH =================
def pila_colores_valida(texto):
    prof = 0
    for m in PATRON_COLOR_TOKEN.finditer(texto):
        if m.group(1).lower().startswith("{colour_start|"):
            prof += 1
        else:
            prof -= 1
            if prof < 0:
                return False
    return prof == 0


def reparar_colores_en_texto(texto):
    nuevo = PATRON_COLOR_ROTO.sub("", texto)
    if pila_colores_valida(nuevo):
        return nuevo, (nuevo != texto)

    # 1) Corregir pares invertidos ({colour_end}...{colour_start|X})
    for _ in range(10):
        tokens = list(PATRON_COLOR_TOKEN.finditer(nuevo))
        prof = 0
        intercambiado = False
        for i, m in enumerate(tokens):
            if m.group(1).lower().startswith("{colour_start|"):
                prof += 1
            else:
                if (
                    prof == 0
                    and i + 1 < len(tokens)
                    and tokens[i + 1].group(1).lower().startswith("{colour_start|")
                ):
                    m_end = m
                    m_start = tokens[i + 1]
                    medio = nuevo[m_end.end() : m_start.start()]
                    lead = medio[: len(medio) - len(medio.lstrip(" \t"))]
                    trail = medio[len(medio.rstrip(" \t")) :]
                    core = medio.strip(" \t")
                    sufijo = nuevo[m_start.end() :]
                    esp_fin = trail if (trail and sufijo and sufijo[0] not in ".,;:!?)]}") else ""
                    reemplazo = f"{lead}{m_start.group(1)}{core}{m_end.group(1)}{esp_fin}"
                    nuevo = nuevo[: m_end.start()] + reemplazo + sufijo
                    intercambiado = True
                    break
                prof -= 1
        if not intercambiado or pila_colores_valida(nuevo):
            break

    if pila_colores_valida(nuevo):
        return nuevo, True

    # 2) Cerrar etiquetas abiertas que falten al final
    prof = 0
    bajo_cero = False
    for m in PATRON_COLOR_TOKEN.finditer(nuevo):
        prof += 1 if m.group(1).lower().startswith("{colour_start|") else -1
        if prof < 0:
            bajo_cero = True
            break
    if not bajo_cero and prof > 0:
        nuevo = nuevo + ("{colour_end}" * prof)
        if pila_colores_valida(nuevo):
            return nuevo, True

    # 3) Fallback seguro: quitar etiquetas de color rotas conservando el texto en español
    return PATRON_COLOR_TOKEN.sub("", nuevo), True


def firma_specs(texto):
    tipos = []
    for m in PATRON_SPEC_REAL.finditer(texto):
        if m.group(2):
            tipos.append(m.group(3).lower())
    return tipos


def escapar_todos_porcentajes(texto):
    return PATRON_PCT.sub(lambda m: "%%" if m.group(1) else "%" + m.group(0), texto)


def sanear_entrada_completa(eid, txt, orig_lista):
    hubo_cambio = False
    nuevo, cambio_color = reparar_colores_en_texto(txt)
    if cambio_color:
        hubo_cambio = True

    es_tooltip = eid.lower().startswith(PREFIJOS_FORMATEADOS)
    orig_usa_doble_pct = any("%%" in c for c in orig_lista)
    orig_tiene_espacio_pct = any(
        any(m.group(3) for m in PATRON_PCT.finditer(c)) for c in orig_lista
    )

    def reemplazar_pct(m):
        if m.group(1):
            return m.group(1)
        if m.group(2):
            return m.group(2)
        if m.group(3):
            return ("%" + m.group(3)) if not orig_tiene_espacio_pct else m.group(3)
        if m.group(4):
            return "%%" if (es_tooltip or orig_usa_doble_pct) else "%"
        return m.group(0)

    saneado = PATRON_PCT.sub(reemplazar_pct, nuevo)
    if saneado != nuevo:
        nuevo = saneado
        hubo_cambio = True

    if nuevo.count("{") != nuevo.count("}"):
        for cand in orig_lista:
            if cand.count("{") == cand.count("}") and pila_colores_valida(cand):
                return cand, True

    if orig_lista:
        firma_es = firma_specs(nuevo)
        firmas_orig = [firma_specs(c) for c in orig_lista]
        if firma_es not in firmas_orig:
            if [] in firmas_orig:
                return escapar_todos_porcentajes(nuevo), True
            mejor_orig = orig_lista[0]
            mejor_orig, _ = reparar_colores_en_texto(mejor_orig)
            mejor_orig = PATRON_PCT.sub(
                lambda m: ("%" + m.group(3))
                if m.group(3)
                else ("%%" if (m.group(4) and es_tooltip) else m.group(0)),
                mejor_orig,
            )
            return mejor_orig, True

    return nuevo, hubo_cambio


# ================= COMPILACIÓN OFICIAL ===================
def limpiar_archivos(carpeta):
    if os.path.isdir(carpeta):
        for f in os.listdir(carpeta):
            p = os.path.join(carpeta, f)
            if os.path.isfile(p):
                os.remove(p)


def compilar_en_localization(ruta_exe, ruta_mod_loc, log_compilador, xml_str, ruta_destino):
    limpiar_archivos(ruta_mod_loc)
    ruta_xml = os.path.join(ruta_mod_loc, "temp_compilar.string_table.xml")
    with open(ruta_xml, "w", encoding="utf-8") as f:
        f.write(xml_str)

    ruta_sp = os.path.join(ruta_mod_loc, "spanish.loc2")

    with open(log_compilador, "w", encoding="utf-8", errors="ignore") as log_f:
        proc = subprocess.Popen(
            [ruta_exe, ruta_xml],
            cwd=ruta_mod_loc,
            stdin=subprocess.PIPE,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            proc.stdin.write(b"\r\n")
            proc.stdin.flush()
            proc.stdin.close()
        except Exception:
            pass

        inicio = time.monotonic()
        ultimo_tam = -1
        estable_desde = None

        while time.monotonic() - inicio < 30:
            if proc.poll() is not None:
                break
            if os.path.isfile(ruta_sp):
                tam = os.path.getsize(ruta_sp)
                if tam > 0:
                    if tam == ultimo_tam:
                        if estable_desde and (time.monotonic() - estable_desde) >= 0.7:
                            break
                    else:
                        ultimo_tam = tam
                        estable_desde = time.monotonic()
            time.sleep(0.15)

        if proc.poll() is None:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.15)

    if not os.path.isfile(ruta_sp) or os.path.getsize(ruta_sp) == 0:
        detalle = ""
        if os.path.isfile(log_compilador):
            detalle = open(log_compilador, "r", encoding="utf-8", errors="ignore").read().strip()
        return False, 0, detalle

    shutil.move(ruta_sp, ruta_destino)
    return True, os.path.getsize(ruta_destino), ""


def cargar_ids_base_juego(ruta_dd):
    ids_base = set()
    carpetas = [os.path.join(ruta_dd, "localization")]
    dlc_dir = os.path.join(ruta_dd, "dlc")
    if os.path.isdir(dlc_dir):
        for raiz, _, _ in os.walk(dlc_dir):
            if os.path.basename(raiz).lower() == "localization":
                carpetas.append(raiz)

    for carpeta in carpetas:
        if not os.path.isdir(carpeta):
            continue
        for f in os.listdir(carpeta):
            if f.lower().endswith(".string_table.xml"):
                bloques = extraer_bloques_xml(os.path.join(carpeta, f))
                for eid, _ in bloques.get("spanish", []):
                    ids_base.add(eid)
    return ids_base


def deduplicar_entradas_de_mod(lista_por_archivo):
    mapa_por_id = {}
    orden_ids = []
    for _, entradas in lista_por_archivo:
        agrupado = {}
        for item in entradas:
            eid = item[0]
            if eid.lower().startswith(PREFIJOS_UNICOS):
                agrupado[eid] = [item]
            else:
                agrupado.setdefault(eid, []).append(item)
        for eid, items in agrupado.items():
            if eid not in mapa_por_id:
                orden_ids.append(eid)
            mapa_por_id[eid] = items

    salida = []
    for eid in orden_ids:
        salida.extend(mapa_por_id[eid])
    return salida


def ejecutar_tarea_traduccion(tarea):
    id_mod, ruta_xml_out, entradas_prep, orig_mod, retraducir = tarea
    if not retraducir and os.path.exists(ruta_xml_out):
        return id_mod, True, "cargado desde XML previo", ruta_xml_out

    por_traducir = []
    meta = []
    finales = [None] * len(entradas_prep)

    for i, (eid, txt, idioma, debe_traducir) in enumerate(entradas_prep):
        if not debe_traducir or not txt.strip():
            finales[i] = (eid, txt)
            continue
        prot, tokens, ei, ef = proteger_codigos(txt)
        if not necesita_traduccion(prot):
            finales[i] = (eid, txt)
            continue
        src_lang = detectar_idioma_origen(prot, idioma)
        por_traducir.append((prot, src_lang))
        meta.append((i, eid, tokens, ei, ef, txt))

    trads, fallos = traducir_textos_por_idioma(por_traducir)
    if fallos > 0:
        return id_mod, False, f"{fallos} textos fallaron", ruta_xml_out

    for trad, (i, eid, tokens, ei, ef, orig) in zip(trads, meta):
        rest, _ = restaurar_codigos(trad, tokens, ei, ef, orig)
        finales[i] = (eid, rest)

    # Aplicar saneadores anti-crash antes de guardar
    finales_saneados = []
    for eid, txt in finales:
        corregido, _ = sanear_entrada_completa(eid, txt, orig_mod.get(eid, []))
        finales_saneados.append((eid, corregido))

    xml_str = construir_xml(finales_saneados, incluir_dummy_en=False)
    with open(ruta_xml_out, "w", encoding="utf-8") as f:
        f.write(xml_str)
    return id_mod, True, f"{len(finales_saneados)} entradas ({len(por_traducir)} traducidas)", ruta_xml_out


# ================= FLUJO PRINCIPAL =======================
def main():
    parser = argparse.ArgumentParser(
        description="Genera y repara Parche_Maestro_ES para todos tus mods de Darkest Dungeon."
    )
    parser.add_argument("--dd", help="Ruta manual a DarkestDungeon")
    parser.add_argument("--workshop", help="Ruta manual a Steam Workshop 262060")
    parser.add_argument(
        "--solo-recompilar",
        action="store_true",
        help="No traduce mods nuevos; solo audita/sanea XML existentes y recompila .loc2",
    )
    parser.add_argument(
        "--retraducir",
        action="store_true",
        help="Regenera todos los XML (reutilizando cache_traducciones.json)",
    )
    args = parser.parse_args()

    if darkest_esta_abierto():
        print("[ERROR] Darkest Dungeon está abierto. Ciérralo antes de ejecutar el parche.")
        sys.exit(1)

    if getattr(sys, "frozen", False):
        ruta_trabajo = os.path.dirname(os.path.abspath(sys.executable))
    else:
        ruta_trabajo = os.path.dirname(os.path.abspath(__file__))
    carpeta_maestro_xml = os.path.join(ruta_trabajo, "salida_xml")
    carpeta_overrides_xml = os.path.join(ruta_trabajo, "salida_xml_overrides")
    archivo_cache = os.path.join(ruta_trabajo, "cache_traducciones.json")
    log_compilador = os.path.join(ruta_trabajo, "ultimo_log_compilador.txt")

    ruta_dd, ruta_ws = detectar_rutas(args.dd, args.workshop)
    ruta_exe = os.path.join(ruta_dd, "_windows", "win32", "localization.exe")
    if not os.path.isfile(ruta_exe):
        print(f"[ERROR] No se encontró localization.exe en: {ruta_exe}")
        sys.exit(1)
    if not os.path.isdir(ruta_ws):
        print(f"[ERROR] No se encontró la carpeta de Workshop: {ruta_ws}")
        sys.exit(1)

    ruta_mod = os.path.join(ruta_dd, "mods", NOMBRE_CARPETA_MOD)
    ruta_mod_loc = os.path.join(ruta_mod, "localization")
    carpeta_listos = os.path.join(ruta_mod, "_loc2_listos")

    os.makedirs(carpeta_maestro_xml, exist_ok=True)
    os.makedirs(carpeta_overrides_xml, exist_ok=True)
    asegurar_project_xml(ruta_mod)
    cargar_cache(archivo_cache)

    print(f"Darkest Dungeon : {ruta_dd}")
    print(f"Steam Workshop  : {ruta_ws}")
    print(f"Carpeta del mod : {ruta_mod}\n")

    print("1/5 Cargando IDs en español del juego base y DLCs...")
    ids_base = cargar_ids_base_juego(ruta_dd)
    print(f"    IDs base protegidos contra duplicación: {len(ids_base)}")

    print("2/5 Analizando mods de Workshop (sin español, español falso, español real y solo-.loc2)...")
    originales_ws = {}
    loc2_por_mod = {}
    mods_override_ids = set()
    ids_espanol_real_ws = set()
    mods_solo_loc2 = []
    tareas_traduccion = []

    mods_dir = [d for d in sorted(os.listdir(ruta_ws)) if os.path.isdir(os.path.join(ruta_ws, d))]

    for id_mod in mods_dir:
        ruta_m = os.path.join(ruta_ws, id_mod)
        xmls_mod = []
        loc2_sp = []
        loc2_otros = {}

        for raiz, _, archivos in os.walk(ruta_m):
            for f in sorted(archivos):
                fl = f.lower()
                rf = os.path.join(raiz, f)
                if fl.endswith(".string_table.xml"):
                    xmls_mod.append((f, rf))
                elif fl.endswith(".loc2"):
                    if fl.endswith("spanish.loc2") and fl != "spanish.loc2":
                        loc2_sp.append(f)
                    elif fl.endswith("english.loc2"):
                        loc2_otros.setdefault("english", rf)
                    elif fl.endswith("schinese.loc2"):
                        loc2_otros.setdefault("schinese", rf)
                    elif fl.endswith("tchinese.loc2"):
                        loc2_otros.setdefault("tchinese", rf)

        if loc2_sp:
            loc2_por_mod[id_mod] = loc2_sp

        # Caso A: Mod solo-.loc2 sin XML ni español (ej. Eos)
        if not xmls_mod and not loc2_sp and loc2_otros:
            src = loc2_otros.get("english") or loc2_otros.get("schinese") or loc2_otros.get("tchinese")
            mods_solo_loc2.append((id_mod, src, f"{id_mod}_spanish.loc2"))
            continue

        if not xmls_mod:
            continue

        en_norm_por_id = {}
        spanish_archivos, en_archivos, sc_archivos, tc_archivos = [], [], [], []
        spanish_ids_mod = set()
        orig_mod = {}

        for fn, rf in xmls_mod:
            bloques = extraer_bloques_xml(rf)
            for lang in ("english", "spanish", "schinese", "tchinese"):
                for eid, txt in bloques.get(lang, []):
                    orig_mod.setdefault(eid, []).append(txt)
            if "english" in bloques:
                en_archivos.append((fn, bloques["english"]))
                for eid, txt in bloques["english"]:
                    en_norm_por_id.setdefault(eid, set()).add(normalizar_cmp(txt))
            if "spanish" in bloques:
                spanish_archivos.append((fn, bloques["spanish"]))
                for eid, _ in bloques["spanish"]:
                    spanish_ids_mod.add(eid)
            if "schinese" in bloques:
                sc_archivos.append((fn, bloques["schinese"]))
            if "tchinese" in bloques:
                tc_archivos.append((fn, bloques["tchinese"]))

        originales_ws[id_mod] = orig_mod

        # Evaluar si tiene "español falso" (texto en inglés dentro de <language id="spanish">)
        comparables = 0
        en_ingles = 0
        for _, entradas in spanish_archivos:
            for eid, txt in entradas:
                norm = normalizar_cmp(txt)
                if len(norm) < 10 or len(norm.split()) < 2:
                    continue
                comparables += 1
                if (eid in en_norm_por_id and norm in en_norm_por_id[eid]) or parece_ingles(txt):
                    en_ingles += 1

        es_falso_espanol = (
            bool(spanish_ids_mod)
            and bool(loc2_sp)
            and comparables >= 3
            and (en_ingles / comparables >= 0.25 or en_ingles >= 15)
        )

        if es_falso_espanol:
            mods_override_ids.add(id_mod)
            lista_por_archivo = []
            ids_vistos = set()

            for fn, entradas in spanish_archivos:
                prep = []
                for eid, txt in entradas:
                    ids_vistos.add(eid)
                    norm = normalizar_cmp(txt)
                    debe = (
                        (eid in en_norm_por_id and norm in en_norm_por_id[eid] and len(norm) >= 2)
                        or parece_ingles(txt)
                        or bool(PATRON_CJK.search(txt))
                    )
                    prep.append((eid, txt, "english", debe))
                lista_por_archivo.append((fn, prep))

            for idioma, lista_arch in (("english", en_archivos), ("schinese", sc_archivos), ("tchinese", tc_archivos)):
                for fn, entradas in lista_arch:
                    prep = []
                    for eid, txt in entradas:
                        if eid not in ids_vistos:
                            ids_vistos.add(eid)
                            prep.append((eid, txt, idioma, True))
                    if prep:
                        lista_por_archivo.append((f"{idioma}_{fn}", prep))

            dedup = deduplicar_entradas_de_mod(lista_por_archivo)
            ruta_out = os.path.join(carpeta_overrides_xml, f"{id_mod}_override.string_table.xml")
            tareas_traduccion.append((id_mod, ruta_out, dedup, orig_mod, args.retraducir))

        elif spanish_ids_mod and loc2_sp:
            # Mod con español real -> proteger sus IDs y traducir solo IDs que le falten
            ids_espanol_real_ws.update(spanish_ids_mod)
            faltantes = []
            vistos_falt = set(spanish_ids_mod)
            for idioma, lista_arch in (("english", en_archivos), ("schinese", sc_archivos), ("tchinese", tc_archivos)):
                for fn, entradas in lista_arch:
                    prep = []
                    for eid, txt in entradas:
                        if eid not in vistos_falt:
                            vistos_falt.add(eid)
                            prep.append((eid, txt, idioma, True))
                    if prep:
                        faltantes.append((f"{idioma}_{fn}", prep))
            if faltantes:
                dedup = deduplicar_entradas_de_mod(faltantes)
                ruta_out = os.path.join(carpeta_maestro_xml, f"{id_mod}_faltantes.string_table.xml")
                tareas_traduccion.append((id_mod, ruta_out, dedup, orig_mod, args.retraducir))
        else:
            # Mod sin español compilado -> traducir y enviar a parche_maestro_spanish.loc2
            # Si ya existía algún XML traducido previo para este mod en salida_xml, se reutiliza
            existentes_mod = glob.glob(os.path.join(carpeta_maestro_xml, f"{id_mod}_*.string_table.xml"))
            if existentes_mod and not args.retraducir:
                continue

            lista_por_archivo = []
            ids_vistos = set()
            for idioma, lista_arch in (
                ("spanish", spanish_archivos),
                ("english", en_archivos),
                ("schinese", sc_archivos),
                ("tchinese", tc_archivos),
            ):
                for fn, entradas in lista_arch:
                    prep = []
                    for eid, txt in entradas:
                        if eid not in ids_vistos:
                            ids_vistos.add(eid)
                            debe = True if idioma != "spanish" else (parece_ingles(txt) or bool(PATRON_CJK.search(txt)))
                            src_i = "english" if idioma == "spanish" else idioma
                            prep.append((eid, txt, src_i, debe))
                    if prep:
                        lista_por_archivo.append((f"{idioma}_{fn}", prep))
            if lista_por_archivo:
                dedup = deduplicar_entradas_de_mod(lista_por_archivo)
                ruta_out = os.path.join(carpeta_maestro_xml, f"{id_mod}_maestro.string_table.xml")
                tareas_traduccion.append((id_mod, ruta_out, dedup, orig_mod, args.retraducir))

    print(f"    Mods analizados: {len(mods_dir)}")
    print(f"    Mods con español falso (overrides): {len(mods_override_ids)}")
    print(f"    Mods solo-.loc2 sin español: {len(mods_solo_loc2)}")
    print(f"    Tareas de traducción/verificación pendientes: {len(tareas_traduccion)}")

    # 3/5 Traducir pendientes
    if not args.solo_recompilar and tareas_traduccion:
        print("\n3/5 Traduciendo mods pendientes...")
        errores = []
        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futuros = {executor.submit(ejecutar_tarea_traduccion, t): t for t in tareas_traduccion}
                hechos = 0
                for fut in as_completed(futuros):
                    id_mod, ok, detalle, _ = fut.result()
                    if ok:
                        hechos += 1
                        print(f"    [{hechos}/{len(tareas_traduccion)}] {id_mod} -> {detalle}")
                        if hechos % 5 == 0:
                            guardar_cache(archivo_cache)
                    else:
                        errores.append((id_mod, detalle))
                        print(f"    [ERROR] {id_mod}: {detalle}")
        finally:
            guardar_cache(archivo_cache)

        if errores:
            print(f"\n[AVISO] {len(errores)} mods fallaron por red/límite temporal. Vuelve a ejecutar el script para completarlos.")
            sys.exit(1)
    else:
        print("\n3/5 Traducción omitida (todo en caché o modo --solo-recompilar).")

    # 4/5 Auditoría anti-crash global (colores invertidos + porcentajes printf) sobre todos los XML
    print("\n4/5 Auditando y reparando tooltips (etiquetas {colour} y variables %)...")
    reparadas_total = 0
    archivos_reparados = 0
    for carpeta in (carpeta_maestro_xml, carpeta_overrides_xml):
        for ruta_xml in sorted(glob.glob(os.path.join(carpeta, "*.string_table.xml"))):
            id_mod = os.path.basename(ruta_xml).split("_", 1)[0]
            orig_mod = originales_ws.get(id_mod, {})
            bloques = extraer_bloques_xml(ruta_xml)
            entradas = bloques.get("spanish", [])
            nuevas = []
            cambio = False
            for eid, txt in entradas:
                corregido, hubo = sanear_entrada_completa(eid, txt, orig_mod.get(eid, []))
                if hubo:
                    cambio = True
                    reparadas_total += 1
                nuevas.append((eid, corregido))
            if cambio:
                archivos_reparados += 1
                with open(ruta_xml, "w", encoding="utf-8") as f:
                    f.write(construir_xml(nuevas, incluir_dummy_en=False))
    print(f"    Entradas saneadas: {reparadas_total} en {archivos_reparados} archivos XML.")

    # 5/5 Compilación final sin duplicados
    print("\n5/5 Compilando archivos .loc2 finales en Parche_Maestro_ES\\localization...")
    os.makedirs(carpeta_listos, exist_ok=True)
    limpiar_archivos(carpeta_listos)
    ids_unicos_usados = set(ids_base)
    dups_bloqueados = 0

    xml_dummy = construir_xml([("parche_maestro_neutralizar", " ")], incluir_dummy_en=True)
    ruta_dummy = os.path.join(carpeta_listos, "_dummy.loc2")
    ok_d, _, err_d = compilar_en_localization(ruta_exe, ruta_mod_loc, log_compilador, xml_dummy, ruta_dummy)
    if not ok_d:
        print(f"[ERROR] localization.exe falló en la prueba inicial:\n{err_d[:600]}")
        sys.exit(1)

    overrides_xml = sorted(glob.glob(os.path.join(carpeta_overrides_xml, "*_override.string_table.xml")))
    compilados = 0
    for idx, ruta_ov in enumerate(overrides_xml, 1):
        id_mod = os.path.basename(ruta_ov).split("_override", 1)[0]
        if id_mod not in loc2_por_mod:
            continue
        nombres_loc2 = loc2_por_mod[id_mod]
        bloques = extraer_bloques_xml(ruta_ov)
        entradas_limpias = []
        for eid, txt in bloques.get("spanish", []):
            if eid.lower().startswith(PREFIJOS_UNICOS):
                if eid in ids_unicos_usados:
                    dups_bloqueados += 1
                    continue
                ids_unicos_usados.add(eid)
            entradas_limpias.append((eid, txt))

        xml_str = construir_xml(entradas_limpias or [("parche_maestro_vacio", " ")], incluir_dummy_en=True)
        principal = nombres_loc2[0]
        ok, tam, err = compilar_en_localization(
            ruta_exe, ruta_mod_loc, log_compilador, xml_str, os.path.join(carpeta_listos, principal)
        )
        if not ok:
            print(f"    [ERROR] No se pudo compilar {principal}: {err[:300]}")
            continue
        for extra in nombres_loc2[1:]:
            shutil.copy2(ruta_dummy, os.path.join(carpeta_listos, extra))
        compilados += 1
        if idx % 20 == 0 or idx == len(overrides_xml):
            print(f"    Overrides compilados: [{idx}/{len(overrides_xml)}] ({principal} -> {tam / 1024:.1f} KB)")

    if os.path.isfile(ruta_dummy):
        os.remove(ruta_dummy)

    # Compilar parche_maestro_spanish.loc2 (nunca llamarlo spanish.loc2 para no pisar el juego base)
    mapa_maestro = {}
    orden_maestro = []
    for ruta_xml in sorted(glob.glob(os.path.join(carpeta_maestro_xml, "*.string_table.xml"))):
        id_mod = os.path.basename(ruta_xml).split("_", 1)[0]
        if id_mod in mods_override_ids:
            continue
        bloques = extraer_bloques_xml(ruta_xml)
        agrupado = {}
        for eid, txt in bloques.get("spanish", []):
            if eid in ids_base or eid in ids_espanol_real_ws:
                dups_bloqueados += 1
                continue
            if eid.lower().startswith(PREFIJOS_UNICOS):
                if eid in ids_unicos_usados:
                    dups_bloqueados += 1
                    continue
                ids_unicos_usados.add(eid)
                agrupado[eid] = [(eid, txt)]
            else:
                agrupado.setdefault(eid, []).append((eid, txt))
        for eid, items in agrupado.items():
            if eid not in mapa_maestro:
                orden_maestro.append(eid)
            mapa_maestro[eid] = items

    entradas_maestras = []
    for eid in orden_maestro:
        entradas_maestras.extend(mapa_maestro[eid])

    xml_maestro = construir_xml(entradas_maestras or [("parche_maestro_vacio", " ")], incluir_dummy_en=True)
    ok_m, tam_m, err_m = compilar_en_localization(
        ruta_exe,
        ruta_mod_loc,
        log_compilador,
        xml_maestro,
        os.path.join(carpeta_listos, "parche_maestro_spanish.loc2"),
    )
    if not ok_m:
        print(f"[ERROR] Falló parche_maestro_spanish.loc2: {err_m[:500]}")
        sys.exit(1)

    for _, src_loc2, dest_name in mods_solo_loc2:
        shutil.copy2(src_loc2, os.path.join(carpeta_listos, dest_name))

    limpiar_archivos(ruta_mod_loc)
    total_final = 0
    for f in sorted(os.listdir(carpeta_listos)):
        if f.lower().endswith(".loc2"):
            shutil.move(os.path.join(carpeta_listos, f), os.path.join(ruta_mod_loc, f))
            total_final += 1
    shutil.rmtree(carpeta_listos, ignore_errors=True)

    print("\n================ RESUMEN FINAL ================")
    print(f"Mod generado en : {ruta_mod}")
    print(f"Overrides compilados (español falso): {compilados}")
    print(f"parche_maestro_spanish.loc2: {tam_m / 1024:.1f} KB ({len(entradas_maestras)} entradas)")
    print(f"Duplicados bloqueados (sin parpadeo): {dups_bloqueados}")
    print(f"Mods solo-.loc2 desbloqueados (sin texto azul): {len(mods_solo_loc2)}")
    print(f"Total de .loc2 instalados: {total_final}")
    print("\nSiguiente paso: abre Darkest Dungeon, activa 'Parche Maestro Traduccion Espanol'")
    print("y colócalo en el puesto #1 (hasta arriba del orden de carga).")


if __name__ == "__main__":
    try:
        main()
    finally:
        if getattr(sys, "frozen", False):
            input("\nPresiona Enter para cerrar...")