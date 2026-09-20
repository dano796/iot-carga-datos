import flask
import mysql.connector
from mysql.connector import Error

# datos de conexion al motor. en este caso el motor está en la misma
# máquina, por eso host='localhost'
DB_HOST = 'localhost'
DB_NAME = 'data'
DB_USER = 'iot'
DB_PASS = 'iot123'

app = flask.Flask(__name__)

def conectar():
    return mysql.connector.connect(host=DB_HOST, database=DB_NAME,
                                   user=DB_USER, password=DB_PASS)

@app.route('/')
def home():
    return 'pagina principal del distribuidor'

@app.route('/borrardb')
def borrardb():
    try:
     con = conectar()
     print(con.is_connected())
     if con.is_connected():
        cur = con.cursor()
        cur.execute("USE data;")
        print("conectado a la base de datos")
        cur.execute("DROP TABLE IF EXISTS datossensor;")
        print("borro la base de datos")
        cur.execute("""CREATE TABLE datossensor (
            idsensor    NUMERIC,
            timestamp   DATETIME,
            temperatura DECIMAL(5,2),
            humedad     DECIMAL(5,2),
            luz         DECIMAL(10,2),
            latitud     DECIMAL(9,6),
            longitud    DECIMAL(9,6),
            altura      DECIMAL(8,2));""")
        print("crea la tabla nueva")
        cur.close()
        con.commit()
        con.close()
    except Error as e:
     print('Error de conexion: ',e)
    return 'creando la tabla de la base de datos'

@app.route('/send_data', methods=['POST'])
def sensor_send():
    datos = flask.request.get_json(force=True)
    print(datos)

    idsensor_t = datos['id']
    temperatura_t = datos['temperatura']
    latitud_t = datos['lat']
    longitud_t = datos['lon']

    try:
     con = conectar()
     if con.is_connected():
       cur = con.cursor()
       cur.execute("USE data;")
       # Los valores viajan aparte de la sentencia (%s), así el motor no
       # confunde un dato con una sentencia SQL. NOW() la pone el servidor
       # ya que el ESP32 no tiene reloj con hora real
       cur.execute("INSERT INTO datossensor (idsensor, timestamp, temperatura, latitud, longitud) VALUES (%s, NOW(), %s, %s, %s);",
                   (idsensor_t, temperatura_t, latitud_t, longitud_t))
       cur.close()
       con.commit()
       con.close()
    except Error as e:
     print("Error con: ", e)
     return "error", 500
    return "ok",201

@app.route('/datos')
def datos():
    try:
     con = conectar()
     cur = con.cursor()
     cur.execute("""SELECT idsensor, DATE_FORMAT(timestamp,'%Y-%m-%d %H:%i:%s'),
                           temperatura, latitud, longitud
                    FROM datossensor ORDER BY timestamp DESC LIMIT 20;""")
     filas = cur.fetchall()
     cur.close()
     con.close()
    except Error as e:
     return {'error': str(e)}, 500
    return {'registros': filas}

if __name__ == '__main__':
        app.run(debug=True,host='0.0.0.0',port=80)
