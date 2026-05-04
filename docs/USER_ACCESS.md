# Gestión de Acceso de Usuarios

## Cómo funciona el acceso

El dashboard usa Google Workspace para autenticación. Los usuarios inician sesión con su cuenta de Google corporativa — no se crean contraseñas dentro del sistema.

**El flujo es:**
1. El usuario entra a la URL del dashboard y hace clic en "Iniciar sesión con Google"
2. Google verifica su identidad (incluyendo 2FA si está activo en Workspace)
3. Si el dominio del email está autorizado, se crea automáticamente una cuenta en el sistema con rol `viewer`
4. El administrador asigna los permisos de tablas desde el panel de administración

---

## Otorgar acceso a un nuevo usuario

No es necesario crear el usuario manualmente. El proceso es:

1. Asegurarse que el usuario tenga una cuenta de Google Workspace con el dominio autorizado (`@monex.cl`)
2. Enviarle la URL del dashboard
3. El usuario inicia sesión con Google — su cuenta se crea automáticamente con rol `viewer` y sin acceso a ninguna tabla
4. El administrador entra al panel de administración → selecciona al usuario recién creado → marca las tablas a las que debe tener acceso

---

## Revocar acceso

Desde el panel de administración:

1. Ingresar al dashboard como administrador
2. Ir a la pestaña **Admin** en el menú lateral
3. Localizar al usuario en la lista
4. Hacer clic en **×** junto a su nombre para eliminarlo

El usuario no podrá volver a ingresar. Si intenta iniciar sesión con Google nuevamente, se le creará una nueva cuenta vacía (sin permisos). Si se quiere bloquear definitivamente, revocar el acceso también desde la consola de Google Workspace (Workspace Admin → Usuarios → seleccionar usuario → Suspender).

---

## Cambiar permisos de tablas

1. Ir a la pestaña **Admin**
2. Hacer clic sobre el usuario en la lista de la izquierda
3. En el panel derecho, marcar o desmarcar las tablas a las que debe tener acceso
4. Los cambios se guardan inmediatamente

---

## Cambiar el rol de un usuario

No hay interfaz para esto — se hace directamente en la base de datos desde el panel de Render.

**Roles disponibles:**
- `viewer` — solo puede ver las tablas que tiene asignadas
- `admin` — accede a todas las tablas, ve el panel de administración y puede gestionar usuarios

**Pasos:**

1. Ir a [dashboard.render.com](https://dashboard.render.com) e ingresar con la cuenta del proyecto
2. Ir a **PostgreSQL** → seleccionar la base de datos del proyecto → pestaña **PSQL Command**
3. Copiar y ejecutar el comando que aparece ahí para abrir una consola SQL
4. Ejecutar:

```sql
UPDATE users SET role = 'admin' WHERE username = 'nombre_usuario';
```

Para volver a `viewer`:

```sql
UPDATE users SET role = 'viewer' WHERE username = 'nombre_usuario';
```

Para ver todos los usuarios y sus roles actuales:

```sql
SELECT id, username, email, role, is_superuser, created_at FROM users;
```

5. Los cambios toman efecto en el próximo inicio de sesión del usuario (el token actual no se ve afectado hasta que venza, máximo 8 horas)

---

## Cambiar la contraseña de la cuenta de administrador

La cuenta `admin` (acceso de emergencia con contraseña) no usa Google. Para cambiar su contraseña se usa la consola del servidor en Render — no requiere instalar nada localmente.

**Pasos:**

1. Ir a [dashboard.render.com](https://dashboard.render.com) → el servicio backend → pestaña **Shell**
2. Ejecutar:
   ```
   python change_password.py
   ```
3. El script pedirá la nueva contraseña dos veces (mínimo 8 caracteres). No se muestra mientras se escribe.
4. Verificar que el login con la nueva contraseña funciona antes de cerrar la sesión actual.

Para cambiar la contraseña de otro usuario:
```
python change_password.py --username nombre_usuario
```

---

## Cuenta de administrador de emergencia

Existe una cuenta `admin` con contraseña que no usa Google. Se accede desde la pantalla de login haciendo clic en **"Acceso de administrador"**. Esta cuenta es para uso técnico únicamente — no debe usarse en el día a día.

Para cambiar la contraseña seguir los pasos de la sección anterior.

---

## Configuración del PC de trabajo (sincronización con Excel)

El PC de trabajo ejecuta un script en segundo plano que lee el Excel en vivo y envía los datos al servidor. Se configura una sola vez.

**Requisitos previos:**
- Python 3.10 o superior instalado ([python.org](https://www.python.org/downloads/))
- Excel abierto con el archivo de datos cargado
- Conexión a internet

**Pasos:**

1. Copiar la carpeta `sync/` del proyecto a cualquier ubicación en el PC (por ejemplo `C:\Monex\sync\`)

2. Dentro de esa carpeta, copiar `.env.example` y renombrarlo a `.env`. Completar los valores:
   ```
   MINIPC_API_URL=https://[url-del-backend].onrender.com
   SYNC_API_KEY=[clave-provista-por-el-administrador]
   EXCEL_WORKBOOK_NAME=[nombre-parcial-del-archivo-xlsx]
   PUSH_INTERVAL_SECONDS=15
   EXCLUDED_SHEETS=
   ```

3. Abrir una terminal (`cmd`) en la carpeta `sync/` e instalar las dependencias:
   ```
   pip install requests python-dotenv openpyxl xlwings
   ```

4. Ejecutar el paso de post-instalación requerido por xlwings en Windows (solo una vez):
   ```
   python -c "import xlwings; print(xlwings.__file__)"
   ```
   Copiar la ruta que imprime, subir dos carpetas para encontrar `pywin32_postinstall.py`, y ejecutar:
   ```
   python C:\ruta\hasta\pywin32_postinstall.py -install
   ```

5. Abrir Excel con el archivo de datos antes de continuar.

6. Hacer clic derecho sobre `registrar_tarea.bat` → **Ejecutar como administrador**. Confirmar el mensaje de éxito.

A partir de ese momento, el script se inicia automáticamente al encender el PC y se reinicia solo si falla. Para verificar que está corriendo, abrir **Programador de tareas** y buscar `Monex Excel Push`. Los registros de actividad se guardan en `sync\excel_push.log`.

Para iniciar el script manualmente sin reiniciar el PC, ejecutar en una terminal:
```
schtasks /run /tn "Monex Excel Push"
```

> **Importante:** Excel debe estar abierto con el archivo de datos cada vez que el script corre. Si Excel está cerrado, el script registra una advertencia y omite ese ciclo — no se pierden datos, simplemente se pausa hasta que Excel esté disponible.

---

## Cambio a dominio personalizado (futuro)

Si en algún momento se configura un dominio propio (ej: `dashboard.monex.cl`) en lugar de la URL de Render:

**1. Actualizar Google Cloud Console**

Ir a [console.cloud.google.com](https://console.cloud.google.com) → el proyecto del dashboard → APIs & Services → Credentials → el cliente OAuth → agregar el nuevo dominio a **Authorized JavaScript origins**.

**2. Actualizar variables de entorno en Render**

Render → backend service → Environment → agregar el nuevo dominio a `ALLOWED_ORIGINS`.

Guardar → el servicio se redespliega automáticamente.
