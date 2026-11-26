# Parche Maestro ES para Mods de Darkest Dungeon

Herramienta en Python (sin dependencias externas) que escanea automáticamente todos tus mods de Steam Workshop para **Darkest Dungeon**, los traduce al español, corrige errores comunes de tooltips y compila todo en un único mod local (`Parche_Maestro_ES`).

## Qué soluciona
- Traduce mods en inglés o chino que no incluyen español.
- Detecta y sobrescribe mods con "español falso" (texto en inglés dentro de archivos `spanish.loc2`).
- Elimina códigos azules (`[<...>]`) en mods que solo incluyen `.loc2` binarios.
- Bloquea entradas y tooltips duplicados que provocan parpadeo en abalorios y descripciones.
- Repara automáticamente porcentajes `%` peligrosos y etiquetas `{colour_start}` / `{colour_end}` invertidas que causan cierres instantáneos al pasar el cursor.
- Mantiene intacto el idioma español base del juego y los DLCs.

## Requisitos
- Windows con **Darkest Dungeon** instalado en Steam.
- **Python 3.8 o superior** (disponible en python.org; marcar *Add Python to PATH* al instalar).

## Uso rápido
1. **Cierra Darkest Dungeon** por completo.
2. Haz doble clic en **`ejecutar.bat`** o abre **`dist/Parche_Maestro_ES_DD.exe`** para iniciar la interfaz gráfica. Para usar la versión de terminal, ejecuta `py -3 dd_parche_espanol.py`.
3. Revisa las rutas del juego y del Workshop en la interfaz y pulsa **Generar / Actualizar Parche**. La primera vez puede tardar unos minutos; las siguientes usa la caché y solo traduce mods nuevos.
4. Abre Darkest Dungeon, haz clic en el **martillo azul** de tu partida, activa **`Parche Maestro Traduccion Espanol`** y súbelo al **puesto #1 (arriba de todos los demás mods)**.

## Opciones avanzadas (terminal)
- `py -3 dd_parche_espanol.py --solo-recompilar`: repara XML existentes y recompila sin traducir mods nuevos.
- `py -3 dd_parche_espanol.py --dd "RUTA" --workshop "RUTA"`: define rutas manualmente si Steam no se detecta solo.