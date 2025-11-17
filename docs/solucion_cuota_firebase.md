# Solución: Error de Cuota Excedida en Firebase (429 Quota Exceeded)

## Problema

Al iniciar la aplicación, aparece el error:
```
ERROR: Error al obtener equipos (activo=None): Timeout of 300.0s exceeded, last exception: 429 Quota exceeded.
```

Este error indica que se ha excedido la cuota de lectura/escritura de Firebase/Firestore.

## Causas Comunes

1. **Plan Gratuito de Firebase (Spark)**
   - Límite: 50,000 lecturas/día
   - Límite: 20,000 escrituras/día
   - La app hace ~6 consultas al iniciar, pero si se reinicia muchas veces puede agotar la cuota

2. **Múltiples Inicios de Aplicación**
   - Cada inicio carga: equipos, clientes, operadores, cuentas, categorías, subcategorías
   - Si se reinicia la app muchas veces (por errores o pruebas), se acumulan lecturas

3. **Consultas con `order_by()`**
   - Las consultas con ordenamiento pueden consumir más recursos
   - Firestore cobra por cada documento leído

4. **Índices Faltantes**
   - Si faltan índices, Firestore puede intentar escanear toda la colección
   - Esto multiplica el número de lecturas

## Soluciones Implementadas en la Aplicación

### 1. Reintentos Automáticos con Exponential Backoff

La aplicación ahora reintenta automáticamente cuando detecta error de cuota:
- Primer intento: inmediato
- Segundo intento: espera 1 segundo
- Tercer intento: espera 2 segundos
- Cuarto intento: espera 4 segundos

Esto permite que si hay un pico temporal de tráfico, la app espere y reintente.

### 2. Pausas Entre Consultas

Se agregaron pausas de 0.3 segundos entre cada consulta durante la inicialización:
```python
equipos = self.fm.obtener_equipos(activo=None)
time.sleep(0.3)  # Pausa
clientes = self.fm.obtener_entidades(tipo='Cliente', activo=None)
time.sleep(0.3)  # Pausa
...
```

Esto distribuye la carga en el tiempo y reduce el riesgo de exceder límites de tasa (rate limits).

### 3. Mensaje de Error Mejorado

Cuando se excede la cuota, la aplicación ahora muestra:
- Identificación clara del problema (Cuota Excedida)
- Instrucciones sobre qué hacer
- Sugerencias de solución

## Soluciones para el Usuario

### Opción 1: Esperar (Más Simple)

1. **Cerrar la aplicación completamente**
2. **Esperar 15-30 minutos**
   - Las cuotas de Firebase se resetean periódicamente
   - En algunos casos se resetean cada hora
3. **Reintentar**

### Opción 2: Verificar Uso en Firebase Console

1. Ir a [Firebase Console](https://console.firebase.google.com/)
2. Seleccionar proyecto `equipos-zoec`
3. Ir a **Firestore Database** → **Usage**
4. Verificar:
   - ¿Cuántas lecturas se han usado hoy?
   - ¿Está cerca del límite?
   - ¿Cuándo se resetea el contador?

### Opción 3: Actualizar Plan de Firebase (Recomendado para Producción)

Si usas la app frecuentemente:

1. Ir a Firebase Console
2. **Settings** (Configuración) → **Usage and billing**
3. Actualizar a plan **Blaze** (pago por uso)
   - Incluye cuota gratuita mensual generosa
   - Solo pagas por lo que excedas
   - Primer millón de lecturas: gratis
   - Costo adicional muy bajo (≈$0.06 por 100,000 lecturas)

### Opción 4: Optimizar Consultas (Avanzado)

Si eres desarrollador:

1. **Revisar índices en Firestore**:
   ```
   Firebase Console → Firestore → Indexes
   ```
   - Asegurar que existen índices para:
     - `equipos.nombre` (ascending)
     - `entidades.tipo` + `entidades.nombre` (composite)

2. **Reducir frecuencia de reinicios**:
   - No reiniciar la app innecesariamente
   - Usar funciones de la app sin cerrar/abrir

3. **Implementar caché local** (futuro):
   - Guardar datos en SQLite local
   - Solo actualizar desde Firebase cuando sea necesario

## Monitoreo de Uso

### Ver Uso Actual

```bash
# Si tienes Firebase CLI instalado
firebase projects:list
firebase use equipos-zoec
firebase firestore:usage
```

### Alertas (Opcional)

Configurar alertas en Firebase Console:
1. **Settings** → **Usage and billing**
2. **Set budget alerts**
3. Recibir email cuando se alcance 80% de la cuota

## Límites del Plan Gratuito (Spark)

| Recurso | Límite Diario | Límite Mensual |
|---------|---------------|----------------|
| Lecturas Firestore | 50,000 | ~1,500,000 |
| Escrituras Firestore | 20,000 | ~600,000 |
| Eliminaciones | 20,000 | ~600,000 |
| Storage transferido | 1 GB/día | ~30 GB/mes |
| Storage almacenado | - | 5 GB |

**Una inicialización de la app consume aprox:**
- 6 consultas base (equipos, clientes, operadores, cuentas, categorías, subcategorías)
- Más las lecturas de documentos individuales
- **Total estimado: 300-500 lecturas** dependiendo del número de registros

Con el límite diario de 50,000:
- **~100-150 inicializaciones posibles por día** en el plan gratuito

## Recomendaciones

### Para Desarrollo/Testing
- Usar el plan gratuito es suficiente
- Evitar reinicios frecuentes innecesarios
- Esperar si se alcanza el límite

### Para Producción
- **Actualizar a plan Blaze** (pago por uso)
- Costo típico: $1-5/mes para app de gestión pequeña
- Implementar caché local para reducir consultas
- Configurar alertas de uso

### Para Emergencias
Si necesitas usar la app urgentemente y alcanzaste el límite:
1. Esperar 1 hora (los límites pueden resetear)
2. O actualizar temporalmente a plan Blaze
3. O usar un proyecto Firebase diferente (solo para emergencia)

## Código Relevante

### Decorador de Reintentos
```python
@retry_on_quota_exceeded(max_retries=3, initial_delay=1.0)
def obtener_equipos(self, activo=None):
    # Consulta a Firestore
    ...
```

### Pausas Entre Consultas
```python
def _cargar_datos_iniciales(self):
    equipos = self.fm.obtener_equipos(activo=None)
    time.sleep(0.3)  # Pausa para evitar rate limiting
    clientes = self.fm.obtener_entidades(tipo='Cliente')
    time.sleep(0.3)
    ...
```

## Soporte

Si el problema persiste después de intentar estas soluciones:

1. Verificar logs en `equipos.log`
2. Confirmar plan de Firebase actual
3. Verificar uso en Firebase Console
4. Considerar actualizar a plan Blaze
5. Revisar que existan los índices necesarios en Firestore

## Referencias

- [Cuotas de Firebase Firestore](https://firebase.google.com/docs/firestore/quotas)
- [Precios de Firebase](https://firebase.google.com/pricing)
- [Optimización de Firestore](https://firebase.google.com/docs/firestore/best-practices)
