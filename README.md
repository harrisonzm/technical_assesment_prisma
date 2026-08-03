# Servicio de solicitudes institucionales

API REST construida con FastAPI y PostgreSQL para registrar, consultar y actualizar solicitudes institucionales. La solución incluye migraciones y datos iniciales con Alembic, un consumidor HTTP independiente, logs persistentes y pruebas automatizadas.

## Inicio rápido

### Requisitos

- Docker Engine o Docker Desktop.
- Docker Compose v2 (`docker compose`).
- Puertos `8000` y `5432` disponibles.

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

| Servicio | Dirección |
| --- | --- |
| API | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| OpenAPI | `http://localhost:8000/openapi.json` |
| PostgreSQL | `localhost:5432` |

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

| Campo | Valores |
| --- | --- |
| `type` | `Acceso a plataforma`, `Soporte técnico`, `Académica`, `Administrativa` |
| `priority` | `Baja`, `Media`, `Alta` |
| `state` | `Recibida`, `En proceso`, `Completada`, `Rechazada` |

Los payloads inválidos, valores fuera del catálogo y campos desconocidos responden con `422 Unprocessable Entity`.

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

## Variables principales

Consulte [.env.example](.env.example) para ver la configuración completa. Las variables más importantes son:

- `DATABASE_URL`, `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD`: conexión y credenciales de PostgreSQL.
- `API_V1_PREFIX`: prefijo de la API; por defecto `/api/v1`.
- `CORS_ORIGINS`: orígenes permitidos.
- `LOG_FILE_PATH`: ubicación del archivo de log dentro del contenedor.
- `CONSUMER_API_URL`: URL utilizada por el consumidor dentro de la red de Docker.
