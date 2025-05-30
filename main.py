import logging
import os # Para leer la variable de entorno PORT
import flask # Solo para referencia, puedes quitarlo si no lo usas directamente

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL LOGGING (haz esto al principio)
# -----------------------------------------------------------------------------
# Configura el logging para que sea detallado y se envíe a la consola (stdout/stderr)
# Render.com captura los logs de la consola.
logging.basicConfig(
    level=logging.DEBUG,  # Nivel más bajo para capturar todo: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s PID:%(process)d %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[logging.StreamHandler()] # Asegura que los logs vayan a la consola
)

logging.info("-----------------------------------------------------")
logging.info("main.py - INICIO DEL SCRIPT")
logging.info(f"Versión de Flask: {flask.__version__}")
logging.info("-----------------------------------------------------")

from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import requests
import tempfile

app = Flask(__name__)
logging.info("Objeto Flask 'app' creado.")

@app.route('/')
def home():
    logging.info("Ruta '/' - Petición recibida.")
    return 'Servidor Flask activo para extraer texto de PDF. Logging configurado y funcionando.'

@app.route('/procesar_pdf', methods=['POST'])
def procesar_pdf():
    logging.info("Ruta '/procesar_pdf' - Petición POST recibida.")
    try:
        data = request.get_json()
        if data is None:
            logging.error("Ruta '/procesar_pdf' - No se recibieron datos JSON o el Content-Type no es application/json.")
            return jsonify({"error": "Request body debe ser JSON"}), 400
        
        pdf_url = data.get('url')
        logging.info(f"Ruta '/procesar_pdf' - URL del PDF recibida: {pdf_url}")

        if not pdf_url:
            logging.warning("Ruta '/procesar_pdf' - No se proporcionó URL del PDF en el JSON.")
            return jsonify({"error": "No se proporcionó URL del PDF"}), 400

        logging.info(f"Ruta '/procesar_pdf' - Descargando PDF desde: {pdf_url}")
        response = requests.get(pdf_url, timeout=30) # Timeout de 30 segundos para la descarga
        # Verificar si la descarga fue exitosa
        response.raise_for_status()  # Esto lanzará una excepción para códigos de error HTTP (4xx o 5xx)
        
        # Loguear un fragmento del contenido para verificar si es un PDF o HTML/Error de Google Drive
        content_type_header = response.headers.get('Content-Type', 'No Content-Type header')
        logging.info(f"Ruta '/procesar_pdf' - PDF descargado. Status: {response.status_code}, Content-Type: {content_type_header}")
        logging.debug(f"Ruta '/procesar_pdf' - Primeros 300 bytes del contenido descargado: {response.content[:300]}")

        # Usar tempfile para guardar el contenido del PDF temporalmente
        # delete=False es necesario si abres por nombre fuera del 'with', pero asegúrate de limpiarlo si es posible
        # o considera abrirlo directamente desde response.content si fitz lo permite sin escribir a disco.
        # Por ahora, mantenemos la escritura a archivo temporal.
        # NOTA: En entornos sin estado como Render (especialmente en tiers gratuitos), el almacenamiento es efímero.
        #       Si el archivo no se borra, podría acumularse si el proceso no se reinicia.
        #       PyMuPDF puede abrir desde bytes: doc = fitz.open(stream=response.content, filetype="pdf") es mejor.
        
        # *** Opción mejorada: Abrir PDF desde bytes en memoria ***
        logging.info("Ruta '/procesar_pdf' - Abriendo PDF desde bytes en memoria con PyMuPDF.")
        doc = fitz.open(stream=response.content, filetype="pdf")
        
        # Si prefieres seguir con el archivo temporal (por ejemplo, si tienes problemas con stream):
        # with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp_file: # delete=True es más seguro
        #     tmp_file.write(response.content)
        #     tmp_file.flush() # Asegurar que todo se escribe al disco antes de que fitz lo lea
        #     logging.info(f"Ruta '/procesar_pdf' - PDF guardado temporalmente en: {tmp_file.name}")
        #     doc = fitz.open(tmp_file.name) # Abrir el archivo temporal

        logging.info(f"Ruta '/procesar_pdf' - PDF abierto con PyMuPDF. Número de páginas: {len(doc)}")
        
        texto_completo = ""
        for i, page in enumerate(doc):
            logging.debug(f"Ruta '/procesar_pdf' - Procesando página {i+1}/{len(doc)}")
            bloques = page.get_text("blocks")
            bloques_ordenados = sorted(bloques, key=lambda b: (b[1], b[0]))
            for b_idx, b in enumerate(bloques_ordenados):
                contenido = b[4].strip()
                if contenido:
                    texto_completo += contenido + "\n"
                    # logging.debug(f"Ruta '/procesar_pdf' - Pág {i+1}, Bloque {b_idx}, Contenido: {contenido[:50]}...") # Log muy verboso
            logging.debug(f"Ruta '/procesar_pdf' - Página {i+1} procesada.")
        
        logging.info(f"Ruta '/procesar_pdf' - Extracción de texto completada. Longitud original del texto: {len(texto_completo)}")
        doc.close() # Cerrar el documento PDF

        # Normalizar texto a UTF-8 limpio
        texto_completo = texto_completo.encode('utf-8', 'ignore').decode('utf-8')
        logging.info(f"Ruta '/procesar_pdf' - Texto normalizado a UTF-8. Nueva longitud: {len(texto_completo)}")

        # Dividir en partes de 8000 caracteres
        partes = [texto_completo[i:i + 8000] for i in range(0, len(texto_completo), 8000)]
        logging.info(f"Ruta '/procesar_pdf' - Texto dividido en {len(partes)} parte(s). Devolviendo respuesta.")
        
        return jsonify({"partes": partes}), 200

    except requests.exceptions.HTTPError as http_err:
        # Errores específicos de la descarga del PDF (4xx, 5xx)
        error_message = f"Error HTTP ({http_err.response.status_code}) al intentar descargar la URL del PDF: {pdf_url}. Detalle: {str(http_err)}"
        logging.error(f"Ruta '/procesar_pdf' - {error_message}")
        if hasattr(http_err.response, 'text'):
            logging.error(f"Ruta '/procesar_pdf' - Contenido de la respuesta del error HTTP: {http_err.response.text[:500]}") # Muestra parte del cuerpo del error
        return jsonify({"error": error_message, "detalle_respuesta_url": http_err.response.text[:500] if hasattr(http_err.response, 'text') else "No details"}), 500
    except fitz.fitz.FitzError as fitz_err: # Error específico de PyMuPDF
        error_message = f"Error de PyMuPDF (fitz) al procesar el archivo (posiblemente no es un PDF válido o está corrupto): {str(fitz_err)}"
        logging.error(f"Ruta '/procesar_pdf' - {error_message}")
        return jsonify({"error": error_message}), 400 # Podría ser un 400 Bad Request si el PDF es el problema
    except Exception as e:
        # Captura cualquier otra excepción
        logging.error(f"Ruta '/procesar_pdf' - Excepción general no esperada: {str(e)}", exc_info=True) # exc_info=True da el traceback completo al log
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

if __name__ == '__main__':
    # Esta sección se usa si ejecutas "python main.py" directamente.
    # Render.com generalmente usa un servidor WSGI como Gunicorn y define el puerto.
    # Leer el puerto de la variable de entorno PORT que Render.com proporciona.
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Iniciando servidor Flask de desarrollo directamente (app.run) en host 0.0.0.0 puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False) # debug=False es mejor para producción o cuando usas logging
