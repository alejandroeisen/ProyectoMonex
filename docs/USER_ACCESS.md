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

La cuenta `admin` (acceso de emergencia con contraseña) no usa Google. Para cambiar su contraseña:

1. Abrir una consola PSQL en Render (ver pasos anteriores)
2. Generar el hash de la nueva contraseña ejecutando esto en el servidor o localmente con Python:

```python
import bcrypt
print(bcrypt.hashpw(b"nueva_contrasena_aqui", bcrypt.gensalt()).decode())
```

3. Copiar el hash generado (empieza con `$2b$...`) y ejecutar en PSQL:

```sql
UPDATE users SET password_hash = '$2b$12$...' WHERE username = 'admin';
```

4. Verificar que el login con la nueva contraseña funciona antes de cerrar la sesión actual

---

## Cuenta de administrador de emergencia

Existe una cuenta `admin` con contraseña que no usa Google. Se accede desde la pantalla de login haciendo clic en **"Acceso de administrador"**. Esta cuenta es para uso técnico únicamente — no debe usarse en el día a día.

Cambiar la contraseña inicial (`admin123`) tras la entrega del sistema siguiendo los pasos de la sección anterior.

---

## Migración de dominio

Al migrar el sistema al dominio del cliente (`monex.cl`):

**1. Actualizar variables de entorno en Render**

Render → backend service → Environment:

| Variable | Valor de prueba | Valor producción |
|---|---|---|
| `ALLOWED_DOMAIN` | `intelimed.ai` | `monex.cl` |
| `GOOGLE_CLIENT_ID` | (el actual) | (el actual, salvo que se cree un proyecto GCP nuevo) |

Guardar → el servicio se redespliega automáticamente.

**2. Actualizar Google Cloud Console**

Ir a [console.cloud.google.com](https://console.cloud.google.com) → el proyecto del dashboard → APIs & Services → Credentials → el cliente OAuth → agregar a **Authorized JavaScript origins**:
- La URL final del frontend (ej: `https://monexfront.onrender.com`)

Si se usa un dominio personalizado en el futuro, agregarlo también aquí.

**3. Limpiar cuentas de prueba**

Las cuentas creadas durante el desarrollo con dominio distinto al de producción pueden eliminarse desde el panel de administración (pestaña Admin → × junto al usuario).

Después del cambio de dominio, esas cuentas no podrán iniciar sesión, pero seguirán existiendo en la base de datos hasta que se eliminen manualmente.
