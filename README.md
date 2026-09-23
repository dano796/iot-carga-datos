# Carga de Datos IoT

Ejercicio de Carga de Datos del curso Internet de las Cosas. Se hace uso de una placa **LilyGO TTGO T-Beam** que lee el sensor y envía la trama a un **orquestador Flask (servidor)** por HTTP; el orquestador es el único que escribe en la base de datos; persiste la trama según sea el caso de ejemplo.

```
   T-Beam  --WiFi / HTTP POST-->  Orquesdador (EC2)  -->  base de datos (persistencia)
```

La transmisión de la trama es igual. El foco del ejercicio está en cambiar **solo el último tramo**, es decir, la manera en como se persiste:

| Caso | Persistencia | Archivo |
|------|--------------------|--------|
| 1 | Archivo local, SQLite | [`caso1-archivo-local/app.py`](caso1-archivo-local/app.py) |
| 2 | Motor local, MariaDB en la misma máquina | [`caso2-motor-local/app_motorlocal.py`](caso2-motor-local/app_motorlocal.py) |
| 3 | Motor externo, Amazon RDS | [`caso3-motor-externo/app_motorexterno.py`](caso3-motor-externo/app_motorexterno.py) |
| 4 | Object storage, Amazon S3 | [`caso4-s3/app_s3.py`](caso4-s3/app_s3.py) |

**Entre el caso 3 y el caso 2 solo hay una línea de diferencia:** la dirección (nombre) del host. Esa es la demostración central del ejercicio. Así, pasar de un motor local a uno administrado en la nube no toca la lógica de la aplicación.

**Para el caso 4 (S3)** cada trama se guarda como un objeto JSON aparte bajo `data/`, y `/borrardb` / `/datos` se redefinen para este modelo de persistencia.

## Trama

```json
{"id": "186841", "lat": 6.245259, "lon": -75.596510, "temperatura": 22.4,
 "metadata": {"campoCifrado": "", "campoIntegridad": ""}}
```

El **timestamp lo pone el servidor** (`NOW()` / `datetime('now')`), no el sensor.

## Rutas del orquestador

Las cuatro son iguales en los casos 1 a 3. El caso 4 (S3) mantiene el mismo contrato pero sin motor relacional detrás.

| Ruta | Método | Casos 1-3 | Caso 4 (S3) |
|------|--------|-----------|-------------|
| `/` | GET | salud del servidor, confirma que el servicio responda | igual |
| `/borrardb` | GET | `DROP` + `CREATE` de la tabla. Deja la base en cero | Vacía el bucket (`delete_objects` sobre todo lo que haya bajo `data/`) |
| `/send_data` | POST | Recibe la trama y la inserta. Devuelve `201` | Recibe la trama y la sube como un objeto JSON nuevo (`put_object`). Devuelve `201` |
| `/datos` | GET | Últimos 20 registros en JSON, para mostrar en el navegador | `list_objects_v2` + `get_object` de los 20 objetos más recientes por `LastModified` |

## Ejecución en cada caso

```bash
cd caso1-archivo-local       # o el caso que sea
python3 -m venv venv
venv/bin/pip install -r requirements.txt
sudo venv/bin/python app.py  # sudo por el puerto 80
```

Luego, desde otra terminal:

```bash
curl http://localhost/borrardb
curl -X POST http://localhost/send_data -H 'Content-Type: application/json' \
  -d '{"id":"186841","lat":6.245259,"lon":-75.596510,"temperatura":22.4,"metadata":{}}'
curl http://localhost/datos
```

Los casos 2 y 3 necesitan además la base y el usuario creados:

```sql
CREATE DATABASE data;
CREATE USER 'iot'@'localhost' IDENTIFIED BY 'iot123';  -- '%' en vez de 'localhost' si es RDS
GRANT ALL PRIVILEGES ON data.* TO 'iot'@'localhost';
FLUSH PRIVILEGES;
```

En RDS el host del usuario va `'%'`, no `'localhost'`: la aplicación conecta desde el EC2, que es **otra máquina**.

El caso 4 no necesita nada de esto (no hay motor), pero sí necesita credenciales de AWS con permisos sobre el bucket. En el EC2 vienen del rol IAM de la instancia; en local, de las variables de entorno estándar de `boto3` (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_DEFAULT_REGION`) o de `~/.aws/credentials`. El código no lleva ninguna credencial escrita.

## TXhttp

[`TXhttp/`](TXhttp/) es el proyecto PlatformIO para `ttgo-t-beam`. No usa LoRa ni la librería `LoRaBoards`: `WiFi.h` y `HTTPClient.h` ya vienen dentro del core de Arduino para ESP32, por eso no hay `lib_deps`.

Lo único que se configura está arriba de [`src/main.cpp`](TXhttp/src/main.cpp):

```c
#define WIFI_SSID   "UPBWiFi"
#define SERVER_URL  "http://<ip-del-ec2>/send_data"
#define NODE_ID     "186841"
#define CICLO_MS    10000
```

Para compilar y cargar:

```bash
cd TXhttp && pio run -t upload
```

> El ESP32 **solo ve redes de 2.4 GHz**.

## Despliegue en el EC2

Los cuatro orquestadores viven en `/home/ubuntu/iot/` (`local/`, `motor/`, `remoto/`, `s3/`), cada uno con su propio virtualenv, y se manejan con systemd. Las unidades están en [`deploy/`](deploy/).

```bash
sudo cp deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start orq-remoto
```

**Los cuatro casos escuchan en el puerto 80, así que solo puede haber uno activo a la vez.** Para cambiar de caso:

```bash
sudo systemctl stop orq-remoto && sudo systemctl start orq-motor
```

Arrancar Flask con `nohup ... &` dentro de un comando SSH **no funciona**, ya que cuelga el canal y al cerrar la sesión se lleva la aplicación. De ahí que se use systemd.

## Estructura

```
.
├── caso1-archivo-local/       SQLite
├── caso2-motor-local/         MariaDB en la misma máquina
├── caso3-motor-externo/       Amazon RDS
├── caso4-s3/                  S3
├── TXhttp/                    proyecto PlatformIO de la T-Beam
└── deploy/                    unidades systemd del EC2
```

Los archivos `.db` no se versionan: se generan solos con `GET /borrardb`.
