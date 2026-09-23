import datetime
import json

import boto3
import flask

# arn:aws:s3:::iot-bucket-186841. ya no hay un motor de base de datos.
# cada trama se guarda como un objeto JSON aparte bajo el prefijo PREFIX
BUCKET = 'iot-bucket-186841'
PREFIX = 'data/'

app = flask.Flask(__name__)
s3 = boto3.client('s3')

@app.route('/')
def home():
    return 'pagina principal del distribuidor'

@app.route('/borrardb')
def borrardb():
    paginator = s3.get_paginator('list_objects_v2')
    borrados = 0
    try:
        for pagina in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
            objetos = pagina.get('Contents', [])
            if not objetos:
                continue
            claves = [{'Key': o['Key']} for o in objetos]
            s3.delete_objects(Bucket=BUCKET, Delete={'Objects': claves})
            borrados += len(claves)
    except Exception as e:
        print('Error borrando el bucket: ', e)
        return 'error', 500
    print(f'borrados {borrados} objetos de s3://{BUCKET}/{PREFIX}')
    return 'bucket vaciado'

@app.route('/send_data', methods=['POST'])
def sensor_send():
    datos = flask.request.get_json(force=True)
    print(datos)

    idsensor_t = datos['id']
    temperatura_t = datos['temperatura']
    latitud_t = datos['lat']
    longitud_t = datos['lon']

    # El timestamp lo pone el servidor (igual que en los otros casos).
    # el ESP32 no tiene reloj de tiempo real.
    ahora = datetime.datetime.now(datetime.timezone.utc)
    registro = {
        'idsensor': idsensor_t,
        'timestamp': ahora.strftime('%Y-%m-%d %H:%M:%S'),
        'temperatura': temperatura_t,
        'latitud': latitud_t,
        'longitud': longitud_t,
    }
    # Un objeto por trama: el nombre lleva el timestamp para que /datos
    # pueda ordenar por LastModified sin tener que leer cada objeto.
    clave = f"{PREFIX}{ahora.strftime('%Y%m%dT%H%M%S%f')}-{idsensor_t}.json"

    try:
        s3.put_object(Bucket=BUCKET, Key=clave,
                       Body=json.dumps(registro).encode('utf-8'),
                       ContentType='application/json')
    except Exception as e:
        print("Error con: ", e)
        return "error", 500
    return "ok", 201

@app.route('/datos')
def datos():
    try:
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
        objetos = sorted(resp.get('Contents', []),
                          key=lambda o: o['LastModified'], reverse=True)[:20]
        filas = []
        for o in objetos:
            body = s3.get_object(Bucket=BUCKET, Key=o['Key'])['Body'].read()
            filas.append(json.loads(body))
    except Exception as e:
        return {'error': str(e)}, 500
    return {'registros': filas}

if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=80)
