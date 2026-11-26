
# Parche Maestro ES — Traductor y Reparador de Mods para Darkest Dungeon

## ¿Por qué existe esta herramienta?

Como jugador con más de 300 horas en **Darkest Dungeon**, llegué al punto de instalar cientos de mods para seguir exprimiendo el juego. El problema llegó rápido: muchísimos mods no están en español y otros, simplemente por tener el juego configurado en nuestro idioma, mostraban textos rotos llenos de código azul (`[<...>]`) que te sacan por completo de la inmersión.

Al ver que no había traducciones actualizadas ni una solución general para reparar esos textos rotos, decidí crear esta herramienta para resolverlo de una vez por todas. No es una traducción literaria perfecta porque usa un traductor público (para que sea 100% gratis y nadie tenga que pagar una API), pero es más que jugable y te permite disfrutar cualquier mod sin tener que ser experto en inglés ni adivinar qué hace un abalorio.

Ojalá te sirva tanto como a mí.

---

## ¿Qué hace automáticamente?

- **Traduce mods en inglés o chino** de tu Steam Workshop al español.
- **Detecta y corrige el "español falso"**: muchos mods incluyen archivos de idioma español cuyo texto sigue en inglés; la herramienta los sobrescribe correctamente.
- **Elimina códigos azules (`[<...>]`)** en mods que solo distribuyen archivos `.loc2` compilados.
- **Adiós al parpadeo en abalorios y tooltips**: bloquea entradas duplicadas que vuelven locas las descripciones.
- **Repara cierres instantáneos (crasheos)**: corrige automáticamente porcentajes `%` peligrosos y etiquetas de color invertidas (`{colour_end}` / `{colour_start}`) que cerraban el juego al pasar el ratón sobre ciertos objetos.
- **Respeta el juego base y tus DLCs**: nunca sobrescribe el español oficial de Darkest Dungeon y todo se compila en un único mod local (`Parche_Maestro_ES`).

---

## Método de uso

### Opción A: Ejecutable (`.exe`) — Recomendada (sin instalar Python)

1. Descarga **`Parche_Maestro_ES_DD.exe`** desde la sección **[Releases](https://github.com/AlexisRTE/DD-Parche-Maestro-ES/releases)** de este repositorio.
2. **Cierra Darkest Dungeon** por completo antes de empezar.
3. Abre **`Parche_Maestro_ES_DD.exe`** (te recomiendo ponerlo dentro de una carpeta propia para que ahí guarde su caché de traducciones).
4. En la ventana que se abre, verifica que las rutas de **Darkest Dungeon** y de **Steam Workshop (`262060`)** aparezcan en verde. Si tu juego está en otro disco, selecciónalas con **Examinar...**.
5. Haz clic en **`Generar / Actualizar Parche`** y espera a que la barra llegue al 100%.
   - *La primera vez tardará unos minutos dependiendo de cuántos mods tengas. Si luego instalas mods nuevos, vuelve a ejecutarlo: reutilizará la caché y solo traducirá lo nuevo.*
6. Abre Darkest Dungeon, haz clic en el **martillo azul** de tu partida, activa **`Parche Maestro Traduccion Espanol`** y súbelo al **puesto #1 (arriba de todos los demás mods)**.

### Opción B: Desde código fuente (Python 3.8+)

1. Descarga el repositorio (`Code → Download ZIP`) y descomprímelo.
2. Cierra Darkest Dungeon y haz doble clic en **`ejecutar.bat`** (o corre `py -3 dd_parche_gui.py`).
3. Sigue los pasos 4 al 6 de arriba.

---

## Aviso sobre Windows Defender / SmartScreen

El ejecutable está empaquetado con PyInstaller y no tiene firma digital comercial, por lo que Windows puede mostrar la pantalla azul de *"Windows protegió su PC"* (haz clic en **Más información → Ejecutar de todas formas**). Todo el código fuente es 100% abierto y está aquí mismo en GitHub por si prefieres revisarlo o ejecutarlo directamente con Python.

---

## Apoyo opcional

Esta herramienta es completamente gratuita y hecha por puro gusto al juego. No pido nada a cambio, pero si te ahorró dolores de cabeza y te nace invitarme un cafecito, se agradece muchísimo:

- **Invítame un cafecito:** https://paypal.me/ARTechStudio 
