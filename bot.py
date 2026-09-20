import sys
import os
import time
import urllib.request
import urllib.parse
import json
import threading

# Forzar el búfer para ver la salida al instante en Pydroid 3
sys.stdout.reconfigure(line_buffering=True)

print("=== INICIANDO BOT WEB3 COMPLETO Y SEGURO ===")

from web3 import Web3

# ==========================================
# CONFIGURACIÓN GENERAL Y SELECTOR DE MODO
# ==========================================
TOKEN_BOT = "8884650695:AAFV_LTL4qf5H2g8B6M6mAt1YZrN03V8UG4"
CHAT_ID = "7357402032"

POLYGON_RPC_URL = "https://polygon.publicnode.com"
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))

PRIVATE_KEY = "TU_CLAVE_PRIVADA_AQUI"
MI_WALLET = "TU_DIRECCION_DE_WALLET_AQUI"

MONEDAS = ["bitcoin", "ethereum", "solana"]
ARCHIVO_ESTADO = "estado_bot_definitivo.json"
ARCHIVO_HISTORIAL = "historial_precios_definitivo.json"
ARCHIVO_AUDITORIA = "auditoria_trades_definitivo.json"
INTERVALO_SEGUNDOS = 60

MODO_SIMULACION = True  # True para simulación, False para real en Polygon
CAPITAL_INICIAL_SIMULADO = 1000.0

def cargar_json(archivo, por_defecto):
    if os.path.exists(archivo):
        try:
            with open(archivo, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return por_defecto

def guardar_json(archivo, datos):
    try:
        with open(archivo, "w") as f:
            json.dump(datos, f)
    except Exception as e:
        print(f"Error al guardar {archivo}: {e}")

def registrar_trade_auditoria(detalle_trade):
    historial = cargar_json(ARCHIVO_AUDITORIA, [])
    historial.append(detalle_trade)
    guardar_json(ARCHIVO_AUDITORIA, historial)

def enviar_mensaje_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
    datos_payload = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': mensaje}).encode('utf-8')
    for _ in range(3):
        try:
            req = urllib.request.Request(url, data=datos_payload, method='POST')
            with urllib.request.urlopen(req, timeout=5) as respuesta:
                return True
        except Exception:
            time.sleep(1)
    return False

def obtener_precios_mercado():
    ids_str = ",".join(MONEDAS)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as respuesta:
                datos = json.loads(respuesta.read().decode())
                return {moneda: float(datos[moneda]['usd']) for moneda in MONEDAS if moneda in datos}
        except Exception:
            time.sleep(2)
    return None

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return 50.0
    ganancias = perdidas = 0
    for i in range(1, len(precios)):
        cambio = precios[i] - precios[i-1]
        if cambio > 0:
            ganancias += cambio
        else:
            perdidas += abs(cambio)
    prom_g = ganancias / periodo
    prom_p = perdidas / periodo
    if prom_p == 0:
        return 100.0
    rs = prom_g / prom_p
    return round(100 - (100 / (1 + rs)), 2)

def calcular_ema(precios, periodo=20):
    if len(precios) == 0:
        return 0.0
    k = 2 / (periodo + 1)
    ema = precios[0]
    for precio in precios[1:]:
        ema = (precio * k) + (ema * (1 - k))
    return ema

def verificar_gas_y_preparar_swap(token_destino, cantidad_usdt):
    if MODO_SIMULACION:
        return True
    if not w3.is_connected():
        return False
    try:
        gas_price_wei = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price_wei, 'gwei')
        if gas_price_gwei > 200:
            return False
        return True
    except Exception:
        return False

# ==========================================
# HILO DE ESCUCHA DE TELEGRAM (MENÚ INTERACTIVO)
# ==========================================
def escuchar_telegram_en_segundo_plano():
    print("Hilo de escucha instantánea de Telegram con menú activado.")
    while True:
        try:
            estado = cargar_json(ARCHIVO_ESTADO, {"last_update_id": 0})
            offset = estado.get("last_update_id", 0) + 1
            url = f"https://api.telegram.org/bot{TOKEN_BOT}/getUpdates?offset={offset}&timeout=2"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as respuesta:
                datos = json.loads(respuesta.read().decode())
                if datos.get("ok") and datos.get("result"):
                    for update in datos["result"]:
                        estado["last_update_id"] = update["update_id"]
                        texto = update.get("message", {}).get("text", "").strip().lower()
                        
                        if texto in ["/menu", "/menú", "/start"]:
                            menu_txt = (
                                "📋 MENÚ DE CONTROL DEL BOT\n\n"
                                "• /estado - Ver posición y capital actual\n"
                                "• /stats - Métricas de rendimiento y winrate\n"
                                "• /auditoria - Últimos trades registrados\n"
                                "• /emergency - Forzar cierre de posición actual"
                            )
                            enviar_mensaje_telegram(menu_txt)
                            
                        elif texto == "/estado":
                            act = estado.get("activo_actual")
                            modo_txt = "Simulación" if MODO_SIMULACION else "Real"
                            resp = f"📊 [ESTADO]\nModo: {modo_txt}\nPosición: {act.upper() if act else 'Ninguna'}"
                            if MODO_SIMULACION:
                                resp += f"\nCapital: ${round(estado.get('capital_simulado', 1000.0), 2)}"
                            enviar_mensaje_telegram(resp)
                            
                        elif texto == "/stats":
                            g = estado.get("operaciones_ganadas", 0)
                            p = estado.get("operaciones_perdidas", 0)
                            total = g + p
                            winrate = (g / total * 100) if total > 0 else 0
                            enviar_mensaje_telegram(f"🏆 [STATS]\nGanadas: {g} | Perdidas: {p} | Winrate: {round(winrate, 1)}%")
                            
                        elif texto == "/auditoria":
                            auditoria = cargar_json(ARCHIVO_AUDITORIA, [])
                            if not auditoria:
                                enviar_mensaje_telegram("📂 [AUDITORÍA]\nAún no hay operaciones registradas en el historial.")
                            else:
                                ultimos = auditoria[-5:]
                                msg_aud = "📂 ÚLTIMOS TRADES (AUDITORÍA):\n"
                                for t in ultimos:
                                    msg_aud += f"\n• {t.get('activo', 'desc').upper()} | {t.get('resultado', 'N/A')}\n  Compra: ${t.get('precio_compra', 0)} -> Venta: ${t.get('precio_venta', 0)} ({t.get('variacion_porcentaje', 0)}%)\n"
                                enviar_mensaje_telegram(msg_aud)
                                
                        elif texto in ["/emergency", "/cerrar", "/panic"]:
                            if estado.get("activo_actual"):
                                estado["forzar_cierre"] = True
                                enviar_mensaje_telegram("🚨 [ALERTA] Cierre de emergencia activado.")
                            else:
                                enviar_mensaje_telegram("ℹ️ No hay posición activa.")
                                
                        guardar_json(ARCHIVO_ESTADO, estado)
        except Exception:
            pass
        time.sleep(2)

# ==========================================
# BUCLE PRINCIPAL DE TRADING
# ==========================================
print("=== BUCLE PRINCIPAL INICIADO ===")
enviar_mensaje_telegram("🤖 [SISTEMA] Bot completo con menú interactivo iniciado.")

hilo_tg = threading.Thread(target=escuchar_telegram_en_segundo_plano, daemon=True)
hilo_tg.start()

try:
    while True:
        estado = cargar_json(ARCHIVO_ESTADO, {
            "activo_actual": None,
            "precio_compra": 0.0,
            "precio_maximo": 0.0,
            "operaciones_ganadas": 0,
            "operaciones_perdidas": 0,
            "capital_simulado": CAPITAL_INICIAL_SIMULADO,
            "last_update_id": 0,
            "forzar_cierre": False,
            "ultimo_reporte_diario": time.time()
        })
        
        historial = cargar_json(ARCHIVO_HISTORIAL, {m: [] for m in MONEDAS})

        tiempo_actual_ts = time.time()
        if tiempo_actual_ts - estado.get("ultimo_reporte_diario", tiempo_actual_ts) > 86400:
            g = estado.get("operaciones_ganadas", 0)
            p = estado.get("operaciones_perdidas", 0)
            cap_actual = estado.get("capital_simulado", CAPITAL_INICIAL_SIMULADO)
            reporte_diario = f"📈 [REPORTE DIARIO]\n- Ganadas: {g}\n- Perdidas: {p}\n- Capital: ${round(cap_actual, 2)}"
            enviar_mensaje_telegram(reporte_diario)
            estado["ultimo_reporte_diario"] = tiempo_actual_ts
            guardar_json(ARCHIVO_ESTADO, estado)

        print(f"\n[{time.strftime('%H:%M:%S')}] Analizando mercado...")
        precios_actuales = obtener_precios_mercado()

        if precios_actuales:
            mensaje_ciclo = f"🌐 [MONITOREO INTEGRAL]\n"
            
            for moneda, precio in precios_actuales.items():
                if moneda not in historial:
                    historial[moneda] = []
                historial[moneda].append(precio)
                if len(historial[moneda]) > 40:
                    historial[moneda].pop(0)
                
                rsi = calcular_rsi(historial[moneda])
                ema = calcular_ema(historial[moneda], periodo=15)
                mensaje_ciclo += f"- {moneda.capitalize()}: ${precio} (RSI: {rsi} | EMA: ${round(ema, 2)})\n"

            guardar_json(ARCHIVO_HISTORIAL, historial)

            activo_actual = estado.get("activo_actual", None)
            precio_compra = estado.get("precio_compra", 0.0)
            precio_maximo = estado.get("precio_maximo", precio_compra)
            forzar_cierre = estado.get("forzar_cierre", False)

            if activo_actual:
                precio_actual = precios_actuales.get(activo_actual, 0)
                if precio_actual > precio_maximo:
                    precio_maximo = precio_actual
                    estado["precio_maximo"] = precio_maximo

                variacion_total = ((precio_actual - precio_compra) / precio_compra) * 100 if precio_compra > 0 else 0
                caida_desde_pico = ((precio_actual - precio_maximo) / precio_maximo) * 100 if precio_maximo > 0 else 0
                rsi_activo = calcular_rsi(historial.get(activo_actual, []))

                mensaje_ciclo += f"\n📊 Posición: {activo_actual.upper()} | Var: {round(variacion_total, 2)}% | Pico: ${precio_maximo}"

                condicion_stop_loss = variacion_total <= -1.5
                condicion_take_profit = rsi_activo > 70 or variacion_total >= 3.0
                condicion_trailing = (precio_maximo > precio_compra) and (caida_desde_pico <= -1.2)

                if condicion_stop_loss or condicion_take_profit or condicion_trailing or forzar_cierre:
                    if verificar_gas_y_preparar_swap(activo_actual, 0):
                        if forzar_cierre:
                            res_txt = "🚨 [CIERRE DE EMERGENCIA]"
                        elif variacion_total > 0:
                            estado["operaciones_ganadas"] = estado.get("operaciones_ganadas", 0) + 1
                            res_txt = "🟢 [TAKE PROFIT]"
                        else:
                            estado["operaciones_perdidas"] = estado.get("operaciones_perdidas", 0) + 1
                            res_txt = "🔴 [STOP LOSS]"

                        if MODO_SIMULACION:
                            ganancia_dolares = 10.0 * (variacion_total / 100.0)
                            estado["capital_simulado"] = estado.get("capital_simulado", 1000.0) + ganancia_dolares

                        detalle = {
                            "fecha": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "activo": activo_actual,
                            "precio_compra": precio_compra,
                            "precio_venta": precio_actual,
                            "variacion_porcentaje": round(variacion_total, 2),
                            "resultado": res_txt
                        }
                        registrar_trade_auditoria(detalle)

                        estado["activo_actual"] = None
                        estado["precio_compra"] = 0.0
                        estado["precio_maximo"] = 0.0
                        estado["forzar_cierre"] = False
                        
                        mensaje_ciclo += f"\n\n{res_txt}\nOperación cerrada y registrada."
                        guardar_json(ARCHIVO_ESTADO, estado)

            else:
                mejor_moneda = None
                menor_rsi = 100
                for moneda in MONEDAS:
                    rsi_val = calcular_rsi(historial.get(moneda, []))
                    ema_val = calcular_ema(historial.get(moneda, []), periodo=15)
                    precio_actual_moneda = precios_actuales[moneda]
                    
                    if rsi_val < 48 and precio_actual_moneda > ema_val:
                        if rsi_val < menor_rsi:
                            menor_rsi = rsi_val
                            mejor_moneda = moneda

                if mejor_moneda:
                    precio_actual = precios_actuales[mejor_moneda]
                    if verificar_gas_y_preparar_swap(mejor_moneda, 10):
                        estado["activo_actual"] = mejor_moneda
                        estado["precio_compra"] = precio_actual
                        estado["precio_maximo"] = precio_actual
                        estado["forzar_cierre"] = False
                        mensaje_ciclo += f"\n\n🟢 [COMPRA EJECUTADA]\nActivo: {mejor_moneda.upper()} a ${precio_actual} (RSI: {menor_rsi})"
                        guardar_json(ARCHIVO_ESTADO, estado)
                else:
                    mensaje_ciclo += f"\n⏳ Buscando entrada óptima..."

            enviar_mensaje_telegram(mensaje_ciclo)
        else:
            print("Fallo temporal de red al obtener precios.")

        print(f"Esperando {INTERVALO_SEGUNDOS} segundos...")
        time.sleep(INTERVALO_SEGUNDOS)

except KeyboardInterrupt:
    print("\nBot detenido por el usuario.")
    enviar_mensaje_telegram("🛑 [SISTEMA] Bot detenido.")
             Subiendo script del bot 
