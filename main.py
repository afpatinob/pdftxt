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
        response = requests.get(pdf_url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(response.content)
            ruta = tmp_file.name

        doc = fitz.open(ruta)
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        doc.close()

        return jsonify({"texto": texto[:15000]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
