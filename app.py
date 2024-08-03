import os
from flask import Flask, request, render_template, send_file, redirect, url_for, session, jsonify, after_this_request
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
# app.secret_key = 'supersecretkey'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    images = session.get('images', [])
    return render_template('index.html', images=images)

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return redirect(request.url)
    
    if 'images' not in session:
        session['images'] = []

    for file in files:
        if file and file.filename.endswith(('jpg', 'jpeg', 'png')):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            session['images'].append(file_path)
    
    session.modified = True 
    return redirect(url_for('index'))

@app.route('/reorder', methods=['POST'])
def reorder_images():
    order = request.json.get('order', [])
    if 'images' in session:
        try:
            new_order = [session['images'][int(i)] for i in order]
            session['images'] = new_order
            session.modified = True
        except (ValueError, IndexError):
            return jsonify(success=False), 400
    return jsonify(success=True)

@app.route('/convert')
def convert_to_pdf():
    images = session.get('images', [])
    if not images:
        return "No images to convert", 400

    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output.pdf')
    
    pil_images = []
    for img in images:
        try:
            pil_image = Image.open(img).convert('RGB')
            pil_images.append(pil_image)
        except Exception as e:
            print(f"Error opening image {img}: {e}")

    if pil_images:
        try:
            pil_images[0].save(pdf_path, save_all=True, append_images=pil_images[1:])
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return "Error converting to PDF", 500
    
    session.pop('images', None)
    return redirect(url_for('download_file', filename='output.pdf'))

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    
    @after_this_request
    def remove_file(response):
        try:
            os.remove(file_path)
            clear_upload_folder()
        except Exception as error:
            app.logger.error("Error removing or closing downloaded file handle", error)
        return response
    
    return send_file(file_path, as_attachment=True)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/clear')
def clear_images():
    session.pop('images', None) 
    clear_upload_folder()
    return redirect(url_for('index'))

def clear_upload_folder():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path) and filename != 'output.pdf':
            os.remove(file_path)

if __name__ == '__main__':
    app.run(debug=True)
