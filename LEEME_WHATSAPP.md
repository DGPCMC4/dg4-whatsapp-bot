# Directorio DG4 - Piloto de WhatsApp (desplegado en la nube con Render)

Este mini-servicio es independiente del sistema web principal. Vive en su propia
carpeta `whatsapp/` y usa una **copia exportada** de los datos de contacto
(`instituciones.json`), nunca la base de datos en vivo — así el panel de login
y actualización nunca se expone a internet, solo este servicio de consulta.

## Antes de empezar: mantener los datos sincronizados

Cada vez que quieras que el bot de WhatsApp refleje cambios hechos desde el
panel de Actualización:
1. En tu PC, en la carpeta principal del proyecto, corre:
   ```
   python scripts/exportar_instituciones_json.py
   ```
2. Sube el cambio a GitHub (ver sección 3 de abajo, comandos `git add`/`commit`/`push`).

Render vuelve a desplegar automáticamente en cuanto detecta el cambio — no hay
que hacer nada más del lado de Render.

## 1. Crear la cuenta de GitHub

1. Ve a **github.com** y crea una cuenta con el correo institucional de la DG4.
2. Confirma tu correo cuando te llegue el email de verificación.

## 2. Crear el repositorio

1. Ya dentro de GitHub, clic en el botón **"+"** (arriba a la derecha) → **"New repository"**.
2. Nombre: `dg4-whatsapp-bot`
3. Marca **"Private"** (importante — no público, aunque los datos de contacto reales aún no estén ahí).
4. No marques ninguna otra opción (README, .gitignore, licencia) — las dejamos vacías.
5. Clic en **"Create repository"**.

## 3. Subir el código

Necesitas tener **Git** instalado (si `python --version` te funcionó antes, es fácil que también lo tengas; si no, descárgalo de git-scm.com).

Abre cmd **dentro de la carpeta `whatsapp/`** de tu proyecto y corre, uno por uno:

```
git init
git add .
git commit -m "Primera version del bot de WhatsApp"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/dg4-whatsapp-bot.git
git push -u origin main
```

(Reemplaza `TU-USUARIO` por tu nombre de usuario de GitHub — la URL exacta te la muestra GitHub justo después de crear el repositorio, cópiala de ahí.)

Te va a pedir iniciar sesión la primera vez — sigue las instrucciones en pantalla.

## 4. Crear la cuenta de Render y desplegar

1. Ve a **render.com** y crea una cuenta — puedes usar "Sign up with GitHub" para conectarlo directo, es lo más simple.
2. Clic en **"New +"** → **"Web Service"**.
3. Selecciona el repositorio `dg4-whatsapp-bot` que acabas de subir (si no aparece, dale permiso a Render de verlo, te lo pide en pantalla).
4. Configuración:
   - **Name**: `dg4-whatsapp` (o el que quieras — será parte de tu URL pública)
   - **Region**: la más cercana a México que te ofrezcan
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn bot:app --host 0.0.0.0 --port $PORT`
   - **Plan**: **Free**
5. Antes de crear, busca la sección **"Environment Variables"** y agrega estas tres (con tus valores reales, los mismos que usarías en el `.env`):
   - `PHONE_NUMBER_ID` = `1289099420958972`
   - `WHATSAPP_ACCESS_TOKEN` = (tu token — genera uno nuevo en el panel de Meta para esto)
   - `WHATSAPP_VERIFY_TOKEN` = `dg4-verificacion-2026` (o lo que hayas elegido)
6. Clic en **"Create Web Service"**. Va a tardar unos minutos en construir y arrancar.
7. Cuando termine, Render te da una URL pública tipo `https://dg4-whatsapp.onrender.com`.

## 5. Conectar el webhook en el panel de Meta

1. En Meta for Developers → tu app → WhatsApp → Configuración → **"Webhook"**.
2. **URL de devolución de llamada**:
   ```
   https://dg4-whatsapp.onrender.com/webhook
   ```
3. **Token de verificación**: el mismo que pusiste en `WHATSAPP_VERIFY_TOKEN` en Render.
4. "Verificar y guardar".
5. Suscríbete al campo **"messages"**.

## 6. Probar

Desde uno de los 5 números verificados, escríbele al número de prueba de WhatsApp preguntando algo como "teléfono de SADER".

## Una limitación honesta del plan gratuito de Render

Si el servicio no recibe tráfico por 15 minutos, "se duerme" para ahorrar recursos, y el **primer** mensaje que le llegue después de eso puede tardar hasta 30-60 segundos en responder (mientras "despierta"). Los mensajes siguientes, ya despierto, responden normal (segundos). Para el volumen de uso que estimamos (5 personas, uso ocasional), es muy probable que la mayoría de las veces te toque ese primer mensaje lento del día — vale la pena que el equipo lo sepa, para que no piensen que está roto si tarda un poco la primera vez.

Si esto resulta molesto durante el piloto, la solución es pasar a un plan de pago de Render (~$7 USD/mes) que elimina esa espera — pero para probar y decidir, el gratuito es perfectamente funcional.
