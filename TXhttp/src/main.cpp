// ---------------------------------------------------------------------------
// TXhttp - Ejercicio de carga de datos - Internet de las Cosas
//
// La placa se conecta a una red WiFi y transmite al orquestador (servidor
// Flask) la trama del sensor por HTTP. El orquestador se encarga de
// persistir la trama según el caso de ejemplo
//
//      T-Beam  --WiFi/HTTP POST-->  Orquestador  -->  persistencia
//
// La trama emitida es:
//
//   {"id": "186841","lat": 6.245259, "lon": -75.596510, "temperatura" : 22.4,
//    "metadata":{"campoCifrado":"","campoIntegridad":""}}
// ---------------------------------------------------------------------------

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

// --------------
// CONFIGURACIÓN
// --------------

#define WIFI_SSID       "UPBWiFi"
#define WIFI_PASS       ""

// direccion del orquestador
#define SERVER_URL      "http://34.235.40.94/send_data"

#define NODE_ID         "186841"
#define CICLO_MS        10000

// coordenadas fijas para probar la cadena. con el GPS real,
// latitud y longitud de TinyGPSPlus
#define LAT_FIJA        6.245259
#define LON_FIJA       -75.596510

// ---------------------------------------------------------------------------
// Estado
// ---------------------------------------------------------------------------

static char  payload[256];
static float temperatura = 23.0f;  // arranque de la temperatura simulada
static int   contador    = 0;

// ---------------------------------------------------------------------------
// WiFi
// ---------------------------------------------------------------------------

// Conecta (o reconecta) a la red. Devuelve true si quedo conectada.
// Se llama tanto en setup() como en cada ciclo: si el router se cae o la
// placa se aleja, el proximo ciclo la vuelve a levantar sola.
static bool conectarWiFi()
{
    if (WiFi.status() == WL_CONNECTED) {
        return true;
    }

    Serial.printf("WiFi......... conectando a \"%s\"", WIFI_SSID);

    // WIFI_STA = la placa es cliente de un router. Sin esto el core puede
    // dejar activo el modo punto de acceso y la conexion no levanta.
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    // Espera hasta 15 s. No se usa delay() largo para poder ir imprimiendo.
    unsigned long inicio = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - inicio < 15000) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("WiFi......... conectado, IP local ");
        Serial.println(WiFi.localIP());
        Serial.printf("WiFi......... RSSI %d dBm\n", WiFi.RSSI());
        return true;
    }

    Serial.println("WiFi......... FALLO. Revise SSID, clave y que la red sea 2.4 GHz");
    return false;
}

// ---------------------------------------------------------------------------
// Lectura del sensor
// ---------------------------------------------------------------------------

// Temperatura simulada: varía un poquito en cada ciclo y se mantiene en un
// rango creíble. Para usar el HDC1080 real, esta funcion es lo unico que
// cambia (leer el sensor y devolver el valor).
static float leerTemperatura()
{
    temperatura += (random(-30, 31) / 100.0f);   // +/- 0.30 C por ciclo
    if (temperatura < 18.0f) temperatura = 18.0f;
    if (temperatura > 30.0f) temperatura = 30.0f;
    return temperatura;
}

// ---------------------------------------------------------------------------
// Armado de la trama
// ---------------------------------------------------------------------------

static void armarPayload(float temp)
{
    snprintf(payload, sizeof(payload),
             "{\"id\": \"" NODE_ID "\",\"lat\": %.6f, \"lon\": %.6f, "
             "\"temperatura\" : %.1f, "
             "\"metadata\":{\"campoCifrado\":\"\",\"campoIntegridad\":\"\"}}",
             LAT_FIJA,
             LON_FIJA,
             temp);
}

// ---------------------------------------------------------------------------
// Envío
// ---------------------------------------------------------------------------

static void enviar()
{
    WiFiClient  cliente;
    HTTPClient  http;

    if (!http.begin(cliente, SERVER_URL)) {
        Serial.println("HTTP......... URL mal formada, revise SERVER_URL");
        return;
    }

    http.addHeader("Content-Type", "application/json");
    http.setConnectTimeout(5000);
    http.setTimeout(5000);

    int codigo = http.POST((uint8_t *)payload, strlen(payload));

    if (codigo > 0) {
        // Codigo positivo = el servidor respondió. 201 es el "creado" que
        // devuelve el orquestador cuando el INSERT salio bien.
        String respuesta = http.getString();
        Serial.printf("HTTP......... %d %s\n",
                      codigo, codigo == 201 ? "(guardado)" : "");
        Serial.print("Respuesta.... ");
        Serial.println(respuesta);
    } else {
        // Codigo negativo = ni siquiera hubo respuesta: no hay ruta hasta el
        // servidor, el puerto esta cerrado o Flask no esta corriendo.
        Serial.printf("HTTP......... error %d: %s\n",
                      codigo, http.errorToString(codigo).c_str());
        Serial.println("              revise IP/puerto, que Flask este arriba");
        Serial.println("              y que el firewall permita el puerto");
    }

    http.end();
}

// ---------------------------------------------------------------------------
// setup / loop
// ---------------------------------------------------------------------------

void setup()
{
    Serial.begin(115200);
    delay(2000);            // le da tiempo al monitor serial de engancharse

    Serial.println();
    Serial.println("TXhttp - carga de datos por HTTP - id " NODE_ID);
    Serial.println("Destino...... " SERVER_URL);

    randomSeed(esp_random());
    conectarWiFi();
}

void loop()
{
    Serial.printf("\n===== ciclo %d =====\n", contador);

    if (conectarWiFi()) {
        float temp = leerTemperatura();
        armarPayload(temp);

        Serial.println("---------- TX ----------");
        Serial.println(payload);
        Serial.printf("Payload...... %u bytes\n", (unsigned)strlen(payload));

        enviar();
        Serial.println("------------------------");
    } else {
        Serial.println("Sin WiFi, se salta este ciclo");
    }

    contador++;
    delay(CICLO_MS);
}
