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
5. Opcionalmente, cambiar el rol a `admin` si corresponde

---

## Revocar acceso

Desde el panel de administración:

1. Ingresar al dashboard como administrador
2. Ir a la pestaña **Admin** en el menú lateral
3. Localizar al usuario en la lista
4. Hacer clic en **×** junto a su nombre para eliminarlo

El usuario no podrá volver a ingresar. Si intenta iniciar sesión con Google nuevamente, se le creará una nueva cuenta vacía (sin permisos). Si se quiere bloquear definitivamente, se debe revocar el acceso desde la consola de Google Workspace.

---

## Cambiar permisos de tablas

1. Ir a la pestaña **Admin**
2. Hacer clic sobre el usuario en la lista de la izquierda
3. En el panel derecho, marcar o desmarcar las tablas a las que debe tener acceso
4. Los cambios se guardan inmediatamente

---

## Cambiar el rol de un usuario

El rol se puede cambiar solo vía base de datos por ahora (no hay UI para esto). Roles disponibles:
- `viewer` — solo puede ver las tablas que tiene asignadas
- `admin` — accede a todas las tablas, ve el panel de administración y puede gestionar usuarios

Para cambiar el rol de un usuario, contactar al administrador técnico.

---

## Cuenta de administrador de emergencia

Existe una cuenta `admin` con contraseña que no usa Google. Se accede desde la pantalla de login haciendo clic en **"Acceso de administrador"**. Esta cuenta es para uso técnico únicamente — no debe usarse en el día a día.

La contraseña de esta cuenta debe cambiarse tras la entrega del sistema. Para cambiarla, contactar al administrador técnico.

---

## Migración de dominio (para el administrador técnico)

Al migrar el sistema al dominio del cliente (`monex.cl`), cambiar las siguientes variables de entorno en Render:

| Variable | Valor de prueba | Valor producción |
|---|---|---|
| `ALLOWED_DOMAIN` | `gmail.com` | `monex.cl` |
| `GOOGLE_CLIENT_ID` | (mismo) | (mismo, salvo que se cree un proyecto GCP nuevo) |

En Google Cloud Console, agregar el dominio de producción a los **Authorized JavaScript origins** del cliente OAuth:
- `https://monexfront.onrender.com` (o el dominio final del cliente)

Después del cambio, cualquier cuenta creada previamente con `@gmail.com` dejará de poder iniciar sesión. Las cuentas existentes pueden eliminarse desde el panel de administración.
