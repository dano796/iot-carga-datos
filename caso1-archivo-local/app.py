from flask import Flask, request
import sqlite3

db_path = 'database.db'

app = Flask(__name__)

@app.route('/')
def home():
    return 'pagina principal'
@app.route('/borrardb')
def borrardb():
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS data")
    cur.execute("CREATE TABLE data (idsensor NUMERIC, timestamp DATETIME, temperatura NUMERIC, latitud NUMERIC, longitud NUMERIC, altura NUMERIC, luz NUMERIC, humedad NUMERIC)")
    con.commit()
    con.close()
    return 'base de datos reinicializada'
@app.route('/send_data', methods=['POST'])
def sensor_send():
    datos = request.get_json(force=True)
    print(datos)
    id_t = datos['id']
    temperatura_t = datos['temperatura']
    latitud_t = datos['lat']
    longitud_t = datos['lon']
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("INSERT INTO data (idsensor, timestamp, temperatura, latitud, longitud) VALUES (?, datetime('now'), ?, ?, ?)",
                (id_t, temperatura_t, latitud_t, longitud_t))
    con.commit()
    con.close()
    return "ok",201

@app.route('/datos')
def datos():
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT * FROM data ORDER BY rowid DESC LIMIT 20")
    filas = cur.fetchall()
    con.close()
    return {'registros': filas}

if __name__ == '__main__':
        app.run(debug=True,host='0.0.0.0',port=80)
