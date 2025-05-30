from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import requests
import tempfile

app = Flask(__name__)

@app.route('/')
def home():
    return 'Servidor Flask activo para extraer texto de PDF'

@app.route('/procesar_pdf', methods=['POST'])
def procesar_pdf():
    data = request.get_json()
    pdf_url = data.get('url')

    if not pdf_url:
        return jsonify({"error": "No se proporcionó URL del PDF"}), 400

    try:
        # Descargar el PDF
        response = requests.get(pdf_url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(response.content)
            ruta = tmp_file.name

        # Abrir PDF y extraer texto por bloques ordenados
        doc = fitz.open(ruta)
        texto_completo = ""
        for page in doc:
            bloques = page.get_text("blocks")
            bloques_ordenados = sorted(bloques, key=lambda b: (b[1], b[0]))  # ordenar por coordenadas (y, x)
            for b in bloques_ordenados:
                contenido = b[4].strip()
                if contenido:  # evitar bloques vacíos
                    texto_completo += contenido + "\n"
        doc.close()

        # Normalizar texto a UTF-8 limpio
        texto_completo = texto_completo.encode('utf-8', 'ignore').decode('utf-8')

        # Dividir en partes de 8000 caracteres
        partes = [texto_completo[i:i + 8000] for i in range(0, len(texto_completo), 8000)]

        return jsonify({"partes": partes})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
