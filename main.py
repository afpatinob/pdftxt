from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import requests
import tempfile
import json

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
        # Descargar PDF
        response = requests.get(pdf_url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(response.content)
            ruta = tmp_file.name

        # Extraer texto por bloques
        doc = fitz.open(ruta)
        texto_completo = ""
        for page in doc:
            bloques = page.get_text("blocks")
            bloques_ordenados = sorted(bloques, key=lambda b: (b[1], b[0]))
            for b in bloques_ordenados:
                contenido = b[4].strip()
                if contenido:
                    texto_completo += contenido + "\n"
        doc.close()

        # Normalizar y dividir
        texto_completo = texto_completo.encode('utf-8', 'ignore').decode('utf-8')
        partes = [texto_completo[i:i + 8000] for i in range(0, len(texto_completo), 8000)]

        return app.response_class(
            response=json.dumps({"partes": partes}, ensure_ascii=False),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
