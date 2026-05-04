# Propuesta de Desarrollo de Software
**Dashboard Interno de Datos Financieros**

---

**Preparado por:** [TU NOMBRE / ENTIDAD]
**Preparado para:** [NOMBRE EMPRESA CLIENTE]
**Fecha:** Abril 2026

---

## Resumen Ejecutivo

Se propone el desarrollo de un dashboard web interno para acceder a datos financieros en tiempo real desde cualquier lugar, reemplazando el flujo actual basado en Excel. La solución permite al equipo consultar información de mercado actualizada sin depender de estar físicamente en la oficina, manteniendo la operativa actual con Xenith y Excel completamente intacta.

---

## Problema que Resuelve

Actualmente los datos de mercado (precios, tasas de cambio, etc.) están disponibles únicamente en el computador de trabajo a través de Excel y Metastock Xenith. Esto impide al equipo acceder a esa información de forma remota, generando dependencia del lugar físico para consultar datos críticos.

---

## Solución Propuesta

Un sistema compuesto por tres partes:

**1. Script en el PC de trabajo**
Un programa que corre en segundo plano en el computador de trabajo actual. Lee los datos en vivo desde Excel cada 5 segundos — incluyendo los valores RTD de Xenith y los cambios manuales ingresados por el equipo, sin necesidad de guardar el archivo. El computador de trabajo no es modificado en ninguna forma visible para el equipo.

**2. Backend en la nube**
Un servidor alojado en la nube recibe los datos enviados desde el PC de trabajo y los almacena en una base de datos. No requiere hardware adicional ni mantenimiento en oficina. Opera las 24 horas de forma autónoma.

**3. Aplicación web interna**
Una interfaz accesible desde cualquier dispositivo con conexión a internet. El acceso se realiza mediante las cuentas de Google Workspace del equipo (@monex.cl) — sin contraseñas adicionales que recordar. Permite consultar las tablas de datos con filtros y búsqueda, con actualización automática cada 5 segundos, sin necesidad de estar en la oficina.

---

## Alcance del Trabajo

### Incluido

- Diseño e implementación de la arquitectura completa del sistema
- Backend con autenticación segura mediante Google Workspace (inicio de sesión con cuenta @monex.cl, sin contraseñas adicionales), tokens de sesión de 8 horas
- Base de datos en la nube con soporte para múltiples tablas con estructuras distintas
- Script de sincronización que lee datos en vivo desde Excel/Xenith cada 5 segundos (sin guardar el archivo), con arranque automático al iniciar sesión en Windows y reinicio automático ante cualquier falla
- Interfaz web con:
  - Página de inicio de sesión
  - Selector de tablas
  - Vista de datos con búsqueda y ordenamiento por columna
  - Actualización automática de datos sin recargar la página
- Panel de administración (accesible vía rol admin):
  - Gestión de usuarios: crear, eliminar, asignar permisos por tabla
  - Estado del sistema en tiempo real (última sincronización, conexión a base de datos)
  - Registro de actividad reciente del script de sincronización
- Logging persistente del script de sincronización con rotación automática
- Despliegue completo en plataforma cloud (Render): backend, base de datos PostgreSQL y frontend
- Configuración del arranque automático del script en el PC de trabajo (sin intervención manual diaria)
- 60 días de soporte post-entrega para estabilización del sistema

### No incluido

- Modificaciones a la configuración de Xenith o Excel en el computador de trabajo
- Integración de fuentes de datos distintas a las hojas de Excel acordadas
- Desarrollo de aplicación móvil nativa
- Funcionalidades adicionales a las descritas en este documento
- Soporte indefinido posterior al período de 60 días

Cualquier trabajo fuera de este alcance será cotizado por separado.

---

## Entregables

| Entregable | Descripción |
|---|---|
| Código fuente completo | Repositorio privado con backend, frontend y scripts de sincronización. Acceso transferido al cliente contra recepción del pago final. |
| Sistema desplegado | Aplicación funcionando en la nube, accesible desde cualquier navegador |
| Script configurado | Script de sincronización instalado y automatizado en el PC de trabajo |
| Documentación | Instrucciones para uso diario, gestión de usuarios y solución de problemas comunes |
| Traspaso | Sesión de entrega explicando el funcionamiento al responsable técnico interno |

---

## Lo que NO cambia para el equipo

- El computador de trabajo sigue funcionando exactamente igual
- Xenith y Excel no son modificados
- El equipo puede seguir usando Excel como siempre — incluyendo agregar filas, editar celdas y trabajar normalmente mientras el script corre en segundo plano
- No se requiere capacitación especial para usar el dashboard
- No se requiere comprar hardware adicional

---

## Inversión

| Concepto | Monto |
|---|---|
| Desarrollo e implementación completa | CLP [PRECIO] |
| **Total** | **CLP [PRECIO]** |

**Condiciones de pago:**
- 50% al inicio del proyecto (CLP [MITAD])
- 50% al momento de la entrega y puesta en marcha (CLP [MITAD])

*Precios en pesos chilenos. Forma de pago a convenir.*

**Costos operativos mensuales (a cargo del cliente):**
| Servicio | Costo estimado |
|---|---|
| Backend + base de datos (Render) | USD ~20–25 / mes |
| Frontend (Render Static Site) | Gratuito |

*Estos costos corresponden a la plataforma de alojamiento (cobrados en USD por Render) y son independientes del desarrollo. Se pueden revisar según el uso real.*

---

## Consideraciones Importantes

- **Uso interno únicamente:** esta solución está diseñada para uso interno del equipo. No está optimizada para ser presentada a clientes externos ni para uso público.
- **Datos en tiempo real:** el sistema actualiza los datos cada 5 segundos. No es una transmisión instantánea tick-a-tick, sino una sincronización periódica adecuada para consulta y seguimiento interno.
- **Dependencia del PC de trabajo:** el dashboard muestra los últimos datos recibidos. Si el PC de trabajo está apagado, los datos en pantalla corresponden a la última sincronización realizada.
- **Primera carga:** la plataforma cloud puede tardar hasta 30 segundos en responder si nadie ha accedido recientemente (comportamiento normal de la capa gratuita de Render). Esto no afecta el funcionamiento normal durante el horario de uso.

---

## Próximos Pasos

1. Aprobación de esta propuesta y pago del 50% inicial
2. Confirmación de la estructura final de las hojas de Excel
3. Desarrollo, configuración y despliegue
4. Período de pruebas con datos reales en el PC de trabajo
5. Entrega formal e inicio del período de soporte

---

*Esta propuesta tiene una validez de 30 días desde la fecha de emisión.*

---

**[TU NOMBRE]**
[tu@email.com]
