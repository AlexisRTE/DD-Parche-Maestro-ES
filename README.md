# Parche Maestro ES — Traductor y Reparador de Mods para Darkest Dungeon
<img ancho="1917" altura="885" alt="imagen" src="https://github.com/user-attachments/assets/f323ceaa-6a0c-48cf-a5d0-9287b3455900" />

## ¿Por qué existe esta herramienta?

Como jugador con más de 300 horas en **La mazmorra más oscura**, llegué al punto de instalar edificios de mods para seguir esperando el juego. El problema llegó rápido: muchos modos mods no están en español y otros, simple por tener el juego configurado en nuestro idioma, mostraban textos rotos llenos de código azul (`[<...>]`) que te sacan por completo de la inmersión.

Al ver que no había traducciones actualizadas ni una solución general para reparar esos textos rotos, decidió crear esta herramienta para resolver de una vista por todas. No es una traducción literaria perfecta porque usa un traductor público (para que sea 100% gratis y nadie tiene que pagar una API), pero es más que jugable y te permite disfrutar cual mod sin tener que ser experimento en inglés ni adivinar qué hace un abalorio.

Ojalá te sirva tanto como a mí.

---

## ¿Qué hace automáticamente?

- **Traduce mods en inglés o chino** de tu Steam Workshop al español.
- **Detecta y corrige el "español falso"**: muchos mods incluyen archivos de idioma español cuyo texto sigue en inglés; la herramienta los sobrescribe correctamente.
- **Elimina códigos azules (`[<...>]`)** en mods que solo distribuyen archivos `.loc2` compilados.
- **Adiós al parpadeo en abalorios y tooltips**: bloquea entradas duplicadas que valen locas las descripciones.
- **Repara cierres instantáneos (crasheos)**: corrige automáticamente porcentajes `%` peligrosos y etiquetas de color invertidas (`{fin_color}` / `{color_inicio}`) que cerró el juego al pasar el rato sobre objetos objetos.
- **Respeta el juego base y tus DLC**: nunca sobrescribe el español oficial de Darkest Dungeon y todo se compila en un único mod local (`Parche_Maestro_ES`).

---

## Método de uso

### Opinión A: Ejecutable (`.exe`) — Recomendada (sin instalar Python)

1. Descargar **`Parche_Maestro_ES_DD.exe`** desde la sección **[Lanzamientos](https://github.com/AlexisRTE/DD-Parche-Maestro-ES/releases)** de este repositorio.
2. **Mazmorra más oscura de Cierra** por completo antes de empezar.
3. Abre **`Parche_Maestro_ES_DD.exe`** (te recomiendo ponerlo dentro de una alfombra propiedad para que ahí guarde su caché de traducciones).
4. En la ventana que se abre, verifica que las rutas de **La mazmorra más oscura** y de **Taller de vapor (`262060`)** aparezcan en verde. Si tu juego está en otro disco, selecciones con **Examinador...**.
5. Haz clic en **`Generar / Actualizar Parche`** y espera a que la barra llegue al 100%.
   - *La primera vez tarde unos minutos dependientes de clientes mods tengas. Si luego instalaciones mods nuevos, vale a ejecutarlo: reutilizará la caché y solo traducirá lo nuevo.*
6. Abre la mazmorra más oscura, haz clic en el **martillo azul** de tu parte, activa **`Parque Maestro Traducción Español`** y síbelo al **puerto #1 (arriba de todos los demás mods)**.

### Opinión B: Desde código fuente (Python 3.8+)

1. Descargar el repositorio (`Código → Descargar ZIP`) y descomprímelo.
2. Cierra Darkest Dungeon y haz doble clic en **`ejecutar.bat`** (o corre `py -3 dd_parche_gui.py`).
3. Sigue los pasos 4 al 6 de arriba.

---

## Aviso sobre Windows Defender / SmartScreen

El ejecutable está empaquetado con PyInstaller y no tiene firma comercial digital, por lo que Windows puede perder la bolsa azul de *"Windows Protegió su PC"* (haz clic en **Más información → Ejecutar de todas formas**). Todo el código fuente es 100% abierto y está aquí mismo en GitHub por si antes revisarlo o ejecutarlo directamente con Python.

---

## Apoyo opcional

Esta herramienta es completamente gratuita y aquí por puro gusto al juego. No pido nada a cambio, pero si te ahorró dolores de cabeza y te nace invitado un cafécito, se agredece mucho:

- **Invítame un café:** https://paypal.me/ARTechStudio 
