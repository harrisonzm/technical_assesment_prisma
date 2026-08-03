# Servicio de solicitudes institucionales

API REST construida con FastAPI y PostgreSQL para registrar, consultar y actualizar solicitudes institucionales. La solución incluye migraciones y datos iniciales con Alembic, un consumidor HTTP independiente, logs persistentes y pruebas automatizadas.

La capa HTTP incluye compresión GZip, caché Redis con TTL para consultas `GET` y una cola acotada que limita el trabajo concurrente. Una respuesta servida desde caché incluye `X-Cache: HIT`; cualquier `POST`, `PATCH`, `PUT` o `DELETE` exitoso incrementa la versión compartida de la caché para invalidarla en todas las réplicas. Si Redis no está disponible, la API continúa funcionando sin caché.

Redis se configura con `REDIS_URL`, `REDIS_TIMEOUT_SECONDS`, `CACHE_TTL_SECONDS` y `CACHE_KEY_PREFIX`. Los demás límites usan `GZIP_MINIMUM_SIZE`, `REQUEST_MAX_CONCURRENCY`, `REQUEST_QUEUE_SIZE` y `REQUEST_QUEUE_TIMEOUT_SECONDS`. Si la cola está llena se responde `429`; si una petición supera el tiempo máximo de espera se responde `503` y se incluye `Retry-After`.

## Arquitectura

La solución sigue una arquitectura por capas:

```text
Cliente / consumidor HTTP
          │
          ▼
FastAPI ── middleware de logs, cola, GZip y caché Redis
          │
          ▼
Servicio de dominio ── validaciones y reglas de negocio
          │
          ▼
Repositorio SQLAlchemy ── PostgreSQL
```

- **API:** expone los endpoints, valida entradas con Pydantic y transforma errores al formato HTTP común.
- **Servicio:** contiene las reglas para crear, consultar y cambiar el estado de una solicitud.
- **Repositorio:** encapsula las consultas y la persistencia mediante SQLAlchemy asíncrono.
- **PostgreSQL:** conserva solicitudes, restricciones y datos iniciales administrados con Alembic.
- **Redis:** almacena respuestas `GET` con TTL y comparte la caché entre réplicas del backend.
- **Consumidor:** cliente HTTP independiente que genera un lote, aplica reintentos ante errores temporales y consulta las solicitudes creadas.

## Tecnologías

| Tecnología                   | Uso                                                           |
| ----------------------------- | ------------------------------------------------------------- |
| Python 3.12                   | Runtime de la aplicación                                     |
| FastAPI, Starlette y Pydantic | API, middleware, validación y OpenAPI                        |
| SQLAlchemy async y Psycopg    | Acceso asíncrono a PostgreSQL                                |
| PostgreSQL 16                 | Persistencia transaccional                                    |
| Redis 7                       | Caché distribuida de respuestas HTTP                         |
| Alembic                       | Versionado del esquema y carga inicial                        |
| HTTPX                         | Consumidor HTTP y pruebas de integración                     |
| Pytest                        | Pruebas unitarias y de integración                           |
| Docker Compose                | Orquestación local de API, base de datos, Redis y consumidor |

## Inicio rápido

### Requisitos

- Docker Engine o Docker Desktop.
- Docker Compose v2 (`docker compose`).
- Puertos `8000`, `5432` y `6379` disponibles.

### 1. Configurar el entorno

En PowerShell:

```powershell
Copy-Item .env.example .env
```

En Linux o macOS:

```bash
cp .env.example .env
```

Antes de usar la solución fuera de un entorno local, cambie las credenciales y secretos de `.env`, y configure `DEBUG=false`. El archivo `.env` no debe publicarse en el repositorio.

### 2. Construir e iniciar la solución

```bash
docker compose up --build
```

Este comando inicia PostgreSQL, espera a que esté disponible, ejecuta las migraciones, inicia la API y finalmente ejecuta el consumidor. El consumidor procesa un lote y termina; la base de datos y la API continúan activas.

Para ejecutar los servicios en segundo plano:

```bash
docker compose up -d --build
docker compose ps
```

La primera migración crea el esquema y una migración posterior agrega 30 solicitudes de ejemplo. Alembic evita que el seed vuelva a ejecutarse en los siguientes arranques de la misma base de datos.

Servicios disponibles:

| Servicio   | Dirección                             |
| ---------- | -------------------------------------- |
| API        | `http://localhost:8000`              |
| Swagger UI | `http://localhost:8000/docs`         |
| OpenAPI    | `http://localhost:8000/openapi.json` |
| PostgreSQL | `localhost:5432`                     |
| Redis      | `localhost:6379`                     |

### 3. Detener la solución

Si se está ejecutando en primer plano, presione `Ctrl+C`. Luego puede retirar los contenedores conservando los datos y logs:

```bash
docker compose down
```

Para eliminar también la base de datos y los logs persistidos y volver a un estado completamente limpio:

```bash
docker compose down -v
```

> `docker compose down -v` elimina los volúmenes del proyecto. Los datos no se pueden recuperar mediante Docker Compose.

## Probar la API con curl

En PowerShell use `curl.exe` en lugar de `curl` si este último está asociado a `Invoke-WebRequest`.

### Estado de la API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

`/health` comprueba que la aplicación está activa. `/health/ready` también comprueba la conexión con PostgreSQL.

### Crear una solicitud

```bash
curl -X POST http://localhost:8000/api/v1/solicitudes \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: demo-curl-001" \
  -d '{
    "external_id": "EXT-CURL-001",
    "type": "Acceso a plataforma",
    "applicant": "Ada Lovelace",
    "email": "ada@example.com",
    "description": "Solicitud de acceso institucional",
    "priority": "Alta"
  }'
```

La respuesta correcta usa `201 Created`. Repita la petición con el mismo `external_id` para comprobar que los duplicados responden con `409 Conflict`.

### Consultar solicitudes

Todas las solicitudes:

```bash
curl "http://localhost:8000/api/v1/solicitudes?offset=0&limit=20"
```

Filtrar por estado, tipo y prioridad:

```bash
curl --get http://localhost:8000/api/v1/solicitudes \
  --data-urlencode "state=Recibida" \
  --data-urlencode "type=Acceso a plataforma" \
  --data-urlencode "priority=Alta" \
  --data-urlencode "offset=0" \
  --data-urlencode "limit=10"
```

### Consultar una solicitud por ID

Copie el campo `id` devuelto al crear o listar una solicitud y reemplace `<UUID>`:

```bash
curl http://localhost:8000/api/v1/solicitudes/<UUID>
```

Un UUID válido que no exista responde con `404 Not Found`.

### Actualizar el estado

```bash
curl -X PATCH http://localhost:8000/api/v1/solicitudes/<UUID>/estado \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: demo-curl-002" \
  -d '{"state":"En proceso"}'
```

Valores permitidos por la API:

| Campo        | Valores                                                                           |
| ------------ | --------------------------------------------------------------------------------- |
| `type`     | `Acceso a plataforma`, `Soporte técnico`, `Académica`, `Administrativa` |
| `priority` | `Baja`, `Media`, `Alta`                                                     |
| `state`    | `Recibida`, `En proceso`, `Completada`, `Rechazada`                       |

Los payloads inválidos, valores fuera del catálogo y campos desconocidos responden con `422 Unprocessable Entity`.

## Endpoints

| Método   | Ruta                                | Descripción                                         | Respuestas principales    |
| --------- | ----------------------------------- | ---------------------------------------------------- | ------------------------- |
| `GET`   | `/health`                         | Comprueba que el proceso está activo                | `200`                   |
| `GET`   | `/health/ready`                   | Comprueba la conexión con PostgreSQL                | `200`, `503`          |
| `POST`  | `/api/v1/solicitudes`             | Crea una solicitud                                   | `201`, `409`, `422` |
| `GET`   | `/api/v1/solicitudes`             | Lista y filtra solicitudes con`offset` y `limit` | `200`, `422`          |
| `GET`   | `/api/v1/solicitudes/{id}`        | Consulta una solicitud por UUID                      | `200`, `404`, `422` |
| `PATCH` | `/api/v1/solicitudes/{id}/estado` | Actualiza únicamente su estado                      | `200`, `404`, `422` |

El listado admite filtros por `id`, `external_id`, `type`, `applicant`, `email`, `description`, `priority`, `state`, `created_at` y `updated_at`. `limit` acepta valores entre 1 y 100. La especificación completa y los esquemas de respuesta están disponibles en Swagger UI y OpenAPI.

## Usar Postman o Bruno

Los ejemplos anteriores se pueden importar directamente:

- En Postman, seleccione **Import**, elija **Raw text**, pegue un comando curl y confirme la importación.
- En Bruno, abra o cree una colección, seleccione **Import Collection > cURL**, pegue el comando y confirme.

Defina como variable de colección `baseUrl=http://localhost:8000` y reemplace la URL fija por `{{baseUrl}}`. Para los endpoints por ID puede definir además `solicitudId` con el UUID retornado por el POST.

La especificación `http://localhost:8000/openapi.json` también puede importarse en ambas herramientas para generar la colección completa.

## Ejecutar el consumidor nuevamente

El consumidor crea varias solicitudes, consulta sus estados, registra cada resultado y continúa aunque una petición individual falle:

```bash
docker compose run --rm consumer
```

El timeout, los reintentos y el tamaño del lote se configuran en `.env` mediante `CONSUMER_TIMEOUT_SECONDS`, `CONSUMER_MAX_RETRIES`, `CONSUMER_RETRY_DELAY_SECONDS` y `CONSUMER_BATCH_SIZE`.

## Ejecutar las pruebas automatizadas

La imagen de producción solo instala dependencias de runtime. Las dependencias de testing se instalan en el target `test` y se activan mediante el perfil correspondiente:

```bash
docker compose --profile test run --rm test
```

Por grupo:

```bash
docker compose --profile test run --rm test pytest -q tests/unit
docker compose --profile test run --rm test pytest -q tests/integration
```

Las pruebas cubren validaciones, creación, duplicados —incluidos duplicados concurrentes—, consultas, actualización de estado, salud, migraciones, seed, consumidor y logging.

## Logs y diagnóstico

Ver todos los logs en tiempo real:

```bash
docker compose logs -f
```

Ver un servicio específico:

```bash
docker compose logs -f backend
docker compose logs -f consumer
docker compose logs -f db
```

Los logs del backend y del consumidor también se guardan en volúmenes Docker independientes, por lo que sobreviven a `docker compose down`. Incluyen datos como fecha, nivel, servicio, identificador de correlación, método, endpoint, código HTTP, duración e intentos cuando corresponde.

## Migraciones

Las migraciones se aplican automáticamente al iniciar el backend. Para revisar el estado o aplicarlas manualmente con los servicios activos:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

Para recrear la base desde cero y volver a cargar los datos iniciales:

```bash
docker compose down -v
docker compose up --build
```

## Variables de entorno

Consulte [.env.example](.env.example) para copiar la configuración completa.

| Variable                                                  | Valor predeterminado o ejemplo      | Propósito                                                  |
| --------------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------- |
| `ENVIRONMENT`, `DEBUG`                                | `local`, `true`                 | Entorno de ejecución y modo de depuración                 |
| `API_V1_PREFIX`                                         | `/api/v1`                         | Prefijo de los endpoints de negocio                         |
| `SECRET_KEY`                                            | sin valor seguro predeterminado     | Secreto de aplicación; debe cambiarse fuera de local       |
| `CORS_ORIGINS`                                          | lista JSON                          | Orígenes autorizados por CORS                              |
| `DATABASE_URL`                                          | URL de PostgreSQL                   | Conexión usada por SQLAlchemy                              |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | valores de desarrollo               | Inicialización del contenedor PostgreSQL                   |
| `REDIS_URL`                                             | `redis://redis:6379/0`            | Conexión a la caché compartida                            |
| `REDIS_TIMEOUT_SECONDS`                                 | `0.2`                             | Tiempo máximo por operación de caché                     |
| `CACHE_TTL_SECONDS`                                     | `30`                              | Vigencia de una respuesta`GET`; `0` desactiva la caché |
| `CACHE_KEY_PREFIX`                                      | `technical-assessment:http-cache` | Namespace de claves Redis                                   |
| `GZIP_MINIMUM_SIZE`                                     | `500`                             | Tamaño mínimo en bytes para comprimir una respuesta       |
| `REQUEST_MAX_CONCURRENCY`                               | `50`                              | Peticiones procesadas simultáneamente por proceso          |
| `REQUEST_QUEUE_SIZE`                                    | `100`                             | Peticiones adicionales admitidas en espera                  |
| `REQUEST_QUEUE_TIMEOUT_SECONDS`                         | `10`                              | Espera máxima antes de responder`503`                    |
| `LOG_FILE_PATH`                                         | ruta dentro del contenedor          | Archivo de logs estructurados                               |
| `CONSUMER_API_URL`                                      | `http://backend:8000/api/v1`      | URL interna usada por el consumidor                         |
| `CONSUMER_TIMEOUT_SECONDS`                              | `5`                               | Timeout HTTP del consumidor                                 |
| `CONSUMER_MAX_RETRIES`                                  | `3`                               | Reintentos ante conexión fallida o respuesta`5xx`        |
| `CONSUMER_RETRY_DELAY_SECONDS`                          | `1`                               | Pausa entre reintentos                                      |
| `CONSUMER_BATCH_SIZE`                                   | `3`                               | Solicitudes generadas por lote                              |

## Decisiones técnicas

- **Capas API–servicio–repositorio:** separan transporte, negocio y persistencia, facilitando pruebas y cambios de infraestructura.
- **Operaciones asíncronas:** FastAPI, SQLAlchemy y Psycopg evitan bloquear el worker mientras esperan I/O.
- **Idempotencia por `external_id`:** una restricción única en PostgreSQL evita duplicados incluso con peticiones concurrentes; la API devuelve `409`.
- **Caché Redis con cache-aside:** solo se cachean respuestas `GET` exitosas. Las escrituras incrementan una versión compartida y las claves anteriores dejan de ser visibles sin ejecutar borrados masivos.
- **Redis fail-open:** un fallo o timeout de Redis produce un cache miss, pero no impide consultar o modificar PostgreSQL.
- **Cola en el proceso:** limita concurrencia y memoria; devuelve `429` cuando no admite más espera y `503` cuando vence el timeout.
- **Migraciones automáticas:** el contenedor ejecuta `alembic upgrade head` antes de iniciar Uvicorn para mantener el esquema actualizado.
- **Observabilidad:** cada petición recibe un `X-Request-ID` interno y los logs incluyen correlación, duración, endpoint y resultado.

## Limitaciones

- La cola vive dentro de cada proceso y no coordina capacidad global entre varias réplicas.
- La invalidación de caché es global para los endpoints de negocio; una escritura descarta lógicamente todas las consultas cacheadas, aunque solo cambie una solicitud.
- No hay autenticación, autorización, rate limiting por cliente ni terminación TLS en la aplicación.
- Redis se usa como optimización y no como fuente de verdad; al reiniciarlo se pierde la caché, pero no los datos de negocio.
- El consumidor procesa su lote secuencialmente y usa una pausa fija entre reintentos.
- Los logs persisten en volúmenes locales, sin agregación, métricas ni trazas distribuidas.
- La ejecución local expone PostgreSQL y Redis al host; en producción deberían permanecer en una red privada.

## Posibles mejoras

- Evolucionar hacia una arquitectura hexagonal o Clean Architecture, separando el dominio de FastAPI, SQLAlchemy, Redis y HTTP mediante puertos y adaptadores.
- Definir interfaces para repositorios, caché, rate limiting y unidades de trabajo, de forma que la infraestructura pueda sustituirse sin modificar los casos de uso.
- Aplicar patrones de diseño donde aporten valor: Repository y Unit of Work para persistencia transaccional, Strategy para caché y reintentos, Adapter para integraciones externas y Dependency Injection para desacoplar implementaciones.
- Crear casos de uso explícitos —crear, listar, consultar y actualizar solicitudes— y entidades de dominio independientes de Pydantic y SQLAlchemy.
- Invalidar claves específicas o usar etiquetas para conservar resultados no afectados por una escritura.
- Implementar *request coalescing* para evitar que varios misses simultáneos ejecuten la misma consulta.
- Mover la cola a RabbitMQ, Redis Streams, SQS o Kafka si el procesamiento debe ser distribuido y durable.
- Incorporar OAuth2/JWT, autorización por roles, límites diferenciados por identidad y gestión externa de secretos.
- Añadir métricas Prometheus, trazas OpenTelemetry, paneles y alertas.
- Configurar Redis con autenticación, TLS, alta disponibilidad y políticas explícitas de memoria.
- Agregar CI/CD, pruebas de carga y despliegue con varias réplicas detrás de un proxy inverso.
