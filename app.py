from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pymysql
from datetime import datetime
import calendar

app = Flask(__name__)

db = pymysql.connect(
    host='localhost',
    user='root',
    password='',
    database='bancoweb',
    cursorclass=pymysql.cursors.DictCursor
)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['password']
        cursor = db.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        if user and user['password'] == password:
            session['loggedin'] = True
            session['username'] = user['usuario']
            session['user_name'] = f"{user['nombre']} {user['apellido']}"
            session['tipo'] = user['tipo']  # Añadir el tipo de usuario a la sesión

            # Redirigir según el tipo de usuario
            if user['tipo'] == 'cajero':
                return redirect(url_for('operaciones'))
            elif user['tipo'] == 'cliente':
                return redirect(url_for('operacionesClientes'))
            elif user['tipo'] == 'administrador':
                return redirect(url_for('operacionesAdmin'))  # Redirigir a operacionesAdmin.html
            else:
                return 'Tipo de usuario desconocido.'
        else:
            return 'Login fallido. Por favor, verifica tu usuario y contraseña.'
    return render_template('login.html')

@app.route('/operaciones.html')
def operaciones():
    if 'loggedin' in session and session.get('tipo') == 'cajero':
        user_name = session['user_name']
        return render_template('operaciones.html', user_name=user_name)
    return redirect(url_for('login'))

@app.route('/operacionesClientes.html')
def operacionesClientes():
    if 'loggedin' in session and session.get('tipo') == 'cliente':
        user_name = session['user_name']
        return render_template('operacionesClientes.html', user_name=user_name)
    return redirect(url_for('login'))

@app.route('/operacionesAdmin.html')
def operacionesAdmin():
    if 'loggedin' in session and session.get('tipo') == 'administrador':
        user_name = session['user_name']
        return render_template('operacionesAdmin.html', user_name=user_name)
    return redirect(url_for('login'))



@app.route('/realizarRetiros.html')
def loginRetiros():
    if 'loggedin' in session:
        user_name = session['user_name']
        return render_template('realizarRetiros.html', user_name=user_name)
    return redirect(url_for('login'))

@app.route('/realizarDeposito.html')
def loginDeposito():
    if 'loggedin' in session:
        user_name = session['user_name']
        return render_template('realizarDeposito.html', user_name=user_name)
    return redirect(url_for('login'))

@app.route('/analisis.html')
def loginStatus():
    if 'loggedin' in session:
        user_name = session['user_name']
        return render_template('analisis.html', user_name=user_name)
    return redirect(url_for('login'))

@app.route('/realizarTransferencias.html')
def loginTransf():
    if 'loggedin' in session:
        user_name = session['user_name']
        username = session['username']
        cursor = db.cursor()
        cursor.execute("SELECT numcuenta FROM cuentas WHERE cedula = (SELECT cedula FROM usuarios WHERE usuario = %s)", (username,))
        cuentas = cursor.fetchall()
        cursor.close()
        return render_template('realizarTransferencias.html', user_name=user_name, cuentas=cuentas)
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/realizarRetiros.html')
def realizar_retiros():
    return render_template('realizarRetiros.html')

@app.route('/realizarDeposito.html')
def realizar_depositos():
    return render_template('realizarDeposito.html')

@app.route('/operaciones.html')
def realizar_op():
    return render_template('operaciones.html')

@app.route('/realizarTransferencias.html')
def realizar_tr():
    return render_template('realizarTransferencias.html')

@app.route('/analisis.html')
def realizar_analisis():
    return render_template('analisis.html')

@app.route('/obtener_cuentas', methods=['POST'])
def obtener_cuentas():
    cedula = request.form['cedula']
    cursor = db.cursor()
    cursor.execute("SELECT numcuenta FROM cuentas WHERE cedula = %s", (cedula,))
    cuentas = cursor.fetchall()
    cursor.close()
    return jsonify(cuentas)


@app.route('/procesar_retiro', methods=['POST'])
def procesar_retiro():
    if 'loggedin' in session:
        cedula = request.form['cedula']
        numcuenta = request.form['numcuenta']
        monto = float(request.form['monto'])
        fecha = request.form['fecha']

        cursor = db.cursor()

        # Verificar y actualizar el saldo de la cuenta
        cursor.execute("SELECT saldo FROM cuentas WHERE cedula = %s AND numcuenta = %s", (cedula, numcuenta))
        cuenta = cursor.fetchone()

        if not cuenta:
            return jsonify({'status': 'error', 'message': 'Cuenta no encontrada.'}), 400

        saldo_actual = cuenta['saldo']

        if saldo_actual < monto:
            return jsonify({'status': 'error', 'message': 'Fondos insuficientes.'}), 400

        nuevo_saldo = saldo_actual - monto
        cursor.execute("UPDATE cuentas SET saldo = %s WHERE cedula = %s AND numcuenta = %s", (nuevo_saldo, cedula, numcuenta))

        # Insertar registro en la tabla retiros
        cursor.execute("INSERT INTO reriros (usuario, cuenta, monto, fecha) VALUES (%s, %s, %s, %s)", (cedula, numcuenta, monto, fecha))

        db.commit()
        cursor.close()

        mensaje = f'Retiro exitoso. Saldo actual: {nuevo_saldo}'

        return jsonify({'status': 'success', 'message': mensaje}), 200

    return jsonify({'status': 'error', 'message': 'Usuario no logeado.'}), 401

@app.route('/procesar_deposito', methods=['POST'])
def procesar_deposito():
    if 'loggedin' in session:
        cedula_beneficiario = request.form['cedula_beneficiario']
        numcuenta = request.form['numcuenta']
        monto = float(request.form['monto'])
        fecha = request.form['fecha']

        cursor = db.cursor()

        # Actualizar saldo de la cuenta beneficiaria
        cursor.execute("SELECT saldo FROM cuentas WHERE cedula = %s AND numcuenta = %s", (cedula_beneficiario, numcuenta))
        cuenta = cursor.fetchone()
        
        if not cuenta:
            cursor.close()
            return jsonify({'status': 'error', 'message': 'Cuenta no encontrada.'}), 400

        saldo_actual = cuenta['saldo']
        nuevo_saldo = saldo_actual + monto
        cursor.execute("UPDATE cuentas SET saldo = %s WHERE cedula = %s AND numcuenta = %s", (nuevo_saldo, cedula_beneficiario, numcuenta))

        # Insertar registro en la tabla depositos
        cursor.execute("INSERT INTO depositos (usuario, cuenta, monto, fecha) VALUES (%s, %s, %s, %s)", (cedula_beneficiario, numcuenta, monto, fecha))


        db.commit()
        cursor.close()

        mensaje = f'Depósito realizado con éxito. Saldo actual: {nuevo_saldo}'

        return jsonify({'status': 'success', 'message': mensaje}), 200

    return jsonify({'status': 'error', 'message': 'Usuario no logeado.'}), 401

@app.route('/verificar_cedula', methods=['POST'])
def verificar_cedula():
    cedula = request.form['cedula']
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM cuentas WHERE cedula = %s", (cedula,))
    existe = cursor.fetchone() is not None
    cursor.close()
    return jsonify({'exists': existe})

@app.route('/verificar_cuenta', methods=['POST'])
def verificar_cuenta():
    cedula = request.form['cedula']
    numero_cuenta = request.form['numero_cuenta']
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM cuentas WHERE cedula = %s AND numcuenta = %s", (cedula, numero_cuenta))
    valida = cursor.fetchone() is not None
    cursor.close()
    return jsonify({'valid': valida})

@app.route('/procesar_transferencia', methods=['POST'])
def procesar_transferencia():
    if 'loggedin' in session:
        cedula_beneficiario = request.form['cedula']
        numero_cuenta_beneficiario = request.form['numero_cuenta']
        cuenta_origen = request.form['numcuenta']
        monto = float(request.form['monto'])
        fecha = request.form['fecha']

        cursor = db.cursor()

        # Validar saldo cuenta de origen
        cursor.execute("SELECT saldo FROM cuentas WHERE numcuenta = %s", (cuenta_origen,))
        cuenta_origen_data = cursor.fetchone()
        if not cuenta_origen_data:
            return jsonify({'status': 'error', 'message': 'Cuenta de origen no encontrada.'}), 400
        
        saldo_origen = cuenta_origen_data['saldo']
        if saldo_origen < monto:
            return jsonify({'status': 'error', 'message': 'Fondos insuficientes en cuenta de origen.'}), 400
        
        # Validar cuenta beneficiario
        cursor.execute("SELECT saldo FROM cuentas WHERE cedula = %s AND numcuenta = %s", (cedula_beneficiario, numero_cuenta_beneficiario))
        cuenta_beneficiario_data = cursor.fetchone()
        if not cuenta_beneficiario_data:
            return jsonify({'status': 'error', 'message': 'Cuenta del beneficiario no encontrada.'}), 400
        
        saldo_beneficiario = cuenta_beneficiario_data['saldo']

        # Insertar en tabla transferencias
        cursor.execute("INSERT INTO transferencias (cuentaOrigen, cuentaDestino, monto, fecha) VALUES (%s, %s, %s, %s)", 
                       (cuenta_origen, numero_cuenta_beneficiario, monto, fecha))

        # Realizar transferencia
        nuevo_saldo_origen = saldo_origen - monto
        nuevo_saldo_beneficiario = saldo_beneficiario + monto
        cursor.execute("UPDATE cuentas SET saldo = %s WHERE numcuenta = %s", (nuevo_saldo_origen, cuenta_origen))
        cursor.execute("UPDATE cuentas SET saldo = %s WHERE numcuenta = %s", (nuevo_saldo_beneficiario, numero_cuenta_beneficiario))
        db.commit()
        cursor.close()

        return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'error', 'message': 'Usuario no logeado.'}), 401

@app.route('/analisis', methods=['GET', 'POST'])
def analisis():
    if request.method == 'POST':
        data = request.get_json()

        sueldo = data['sueldo']
        vivienda = data['vivienda']
        salud = data['salud']
        alimentacion = data['alimentacion']
        transporte = data['transporte']
        diversion = data['diversion']
        ahorros = data['ahorros']

        total_gastos = vivienda + salud + alimentacion + transporte + diversion + ahorros

        recomendaciones = []

        if vivienda > sueldo * 0.35:
            recomendaciones.append(f"Gastas demasiado en vivienda. Idealmente debería ser el 35% de tu sueldo (máximo: {sueldo * 0.35:.2f}).")
        if alimentacion > sueldo * 0.2:
            recomendaciones.append(f"Gastas demasiado en alimentación. Idealmente debería ser el 20% de tu sueldo (máximo: {sueldo * 0.2:.2f}).")
        if salud > sueldo * 0.15:
            recomendaciones.append(f"Gastas demasiado en salud. Idealmente debería ser el 15% de tu sueldo (máximo: {sueldo * 0.15:.2f}).")
        if transporte > sueldo * 0.15:
            recomendaciones.append(f"Gastas demasiado en transporte. Idealmente debería ser el 15% de tu sueldo (máximo: {sueldo * 0.15:.2f}).")
        if diversion > sueldo * 0.1:
            recomendaciones.append(f"Gastas demasiado en diversión. Idealmente debería ser el 10% de tu sueldo (máximo: {sueldo * 0.1:.2f}).")
        if ahorros < sueldo * 0.15:
            recomendaciones.append(f"No ahorras lo suficiente. Deberías ahorrar al menos el 15% de tu sueldo (mínimo: {sueldo * 0.15:.2f}).")
        if total_gastos > sueldo:
            recomendaciones.append(f"Estás gastando más de lo que ganas. Tu total de gastos ({total_gastos:.2f}) excede tu sueldo ({sueldo:.2f}). Considera reducir tus gastos.")

        return jsonify({
            'recomendaciones': ' '.join(recomendaciones) if recomendaciones else 'Tus gastos están dentro de los límites recomendados.'
        })
    
    return render_template('analisis.html')

@app.route('/retiros.html', methods=['GET'])
def ver_retiros():
    if 'loggedin' in session:
        user_name = session['user_name']
        cursor = db.cursor()

        # Obtener parámetros de búsqueda
        fecha = request.args.get('fecha', '')
        cedula = request.args.get('cedula', '')
        cuenta = request.args.get('cuenta', '')

        # Construir la consulta SQL basada en los parámetros recibidos
        sql = "SELECT id, usuario, cuenta, monto, fecha FROM reriros WHERE 1=1"

        params = []  # Lista para almacenar los parámetros

        if fecha:
            sql += " AND fecha = %s"
            params.append(fecha)
        if cedula:
            sql += " AND usuario = %s"
            params.append(cedula)
        if cuenta:
            sql += " AND cuenta = %s"
            params.append(cuenta)

        # Ejecutar la consulta SQL con los parámetros adecuados
        cursor.execute(sql, params)
        retiros = cursor.fetchall()
        cursor.close()

        return render_template('retiros.html', user_name=user_name, retiros=retiros)

    return redirect(url_for('login'))


@app.route('/depositos.html', methods=['GET'])
def ver_depositos():
    if 'loggedin' in session:
        user_name = session['user_name']
        cursor = db.cursor()

        # Obtener parámetros de búsqueda
        fecha = request.args.get('fecha', '')
        usuario = request.args.get('usuario', '')

        # Construir la consulta SQL basada en los parámetros recibidos
        sql = "SELECT id, usuario, monto, fecha FROM depositos WHERE 1=1"

        params = []  # Lista para almacenar los parámetros

        if fecha:
            sql += " AND fecha = %s"
            params.append(fecha)
        if usuario:
            sql += " AND usuario = %s"
            params.append(usuario)

        # Ejecutar la consulta SQL con los parámetros adecuados
        cursor.execute(sql, params)
        depositos = cursor.fetchall()
        cursor.close()

        return render_template('depositos.html', user_name=user_name, depositos=depositos)

    return redirect(url_for('login'))

@app.route('/transferencias.html', methods=['GET'])
def ver_transferencias():
    if 'loggedin' in session:
        user_name = session['user_name']
        cursor = db.cursor()

        # Obtener parámetros de búsqueda
        fecha = request.args.get('fecha', '')
        cuenta_origen = request.args.get('cuenta_origen', '')
        cuenta_destino = request.args.get('cuenta_destino', '')

        # Construir la consulta SQL basada en los parámetros recibidos
        sql = "SELECT id, cuentaOrigen as cuenta_origen, cuentaDestino as cuenta_destino, monto, fecha FROM transferencias WHERE 1=1"

        params = []  # Lista para almacenar los parámetros

        if fecha:
            sql += " AND fecha = %s"
            params.append(fecha)
        if cuenta_origen:
            sql += " AND cuentaOrigen = %s"
            params.append(cuenta_origen)
        if cuenta_destino:
            sql += " AND cuentaDestino = %s"
            params.append(cuenta_destino)

        # Ejecutar la consulta SQL con los parámetros adecuados
        cursor.execute(sql, params)
        transferencias = cursor.fetchall()
        cursor.close()

        return render_template('transferencias.html', user_name=user_name, transferencias=transferencias)

    return redirect(url_for('login'))

@app.route('/proyeccion', methods=['POST'])
def proyeccion():
    data = request.get_json()
    sueldo = data['sueldo']
    vivienda = data['vivienda']
    salud = data['salud']
    alimentacion = data['alimentacion']
    transporte = data['transporte']
    diversion = data['diversion']
    esporadicos = data['esporadicos']

   
    today = datetime.today()
    current_month = today.month
    remaining_months = 12 - current_month + 1  # Incluir el mes actual

 
    total_ingresos = 0
    total_gastos = 0
    total_saldo = 0


    proyeccion_mensual = []
    for i in range(remaining_months):
        mes = current_month + i
        nombre_mes = calendar.month_name[mes]
        ingreso_mensual = sueldo
        gastos_mensuales = vivienda + salud + alimentacion + transporte + diversion + esporadicos
        saldo_mensual = ingreso_mensual - gastos_mensuales

        total_ingresos += ingreso_mensual
        total_gastos += gastos_mensuales
        total_saldo += saldo_mensual

        proyeccion_mensual.append({
            'mes': nombre_mes,
            'ingreso': ingreso_mensual,
            'gastos': gastos_mensuales,
            'saldo': saldo_mensual
        })

    return jsonify({
        'proyeccion_mensual': proyeccion_mensual,
        'totales': {
            'total_ingresos': total_ingresos,
            'total_gastos': total_gastos,
            'total_saldo': total_saldo
        }
    })

@app.route('/analisis2.html')
def realizar_analisisAnual():
    return render_template('analisis2.html')

if __name__ == '__main__':
    app.secret_key = 'supersecretkey'
    app.run(debug=True, port=5500)
