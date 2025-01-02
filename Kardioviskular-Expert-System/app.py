from flask import Flask, render_template, request, redirect, url_for, session
import os
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

# Fungsi untuk menghitung Certainty Factor (CF)
def calculate_cf(user_cf, expert_cf):
    
    # Hitung CF
    return user_cf * expert_cf

def combine_cf(cf_old, cf_new):
    
    # Gabungkan 2 nilai CF
    return cf_old + cf_new * (1 - cf_old)

# Fungsi untuk mendapatkan nilai CF dari input user
def get_user_cf(choice):
    return {1: 0.0, 2: 0.2, 3: 0.4, 4: 0.6, 5: 0.8, 6: 1.0}.get(choice, 0.0)

# Fungsi untuk membaca knowledge base dari file di direktori data
def load_knowledge_base_from_file():
    knowledge_base = {}
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "knowledge_bases.txt"))
    
    try:
        with open(file_path, 'r') as file:
            penyakit_code = None
            for line in file:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("P"):
                    penyakit_code, penyakit_name = line.split(" - ")
                    knowledge_base[penyakit_code] = {'name': penyakit_name, 'symptoms': {}}
                elif line.startswith("G"):
                    gejala_code, rest = line.split(": ")
                    gejala_name, weight = rest.split(" - ")
                    if penyakit_code:
                        knowledge_base[penyakit_code]['symptoms'][gejala_code] = {'name': gejala_name, 'weight': float(weight)}
        print("Knowledge base berhasil dimuat.")
    except FileNotFoundError:
        print(f"File {file_path} tidak ditemukan.")
    except Exception as e:
        print("Terjadi error saat membaca knowledge base:", e)
    
    return knowledge_base


# Fungsi untuk melakukan diagnosa
def diagnose(gejala_user, knowledge_base):
    hasil_diagnosis = []
    
    # Iterasi melalui setiap penyakit dalam knowledge base
    for penyakit_code, penyakit_data in knowledge_base.items():
        cf_combine = 0.0
        match_found = False
        
        # Iterasi melalui setiap gejala untuk penyakit
        for gejala_code, expert_cf in penyakit_data['symptoms'].items():
            # Cek apakah gejala user cocok dengan gejala penyakit
            user_cf = gejala_user.get(gejala_code, 0.0)
            if user_cf > 0:  # Hanya jika ada CF dari user
                match_found = True  # Menandakan ada kecocokan gejala
                cf_current = calculate_cf(user_cf, expert_cf['weight'])
                cf_combine = combine_cf(cf_combine, cf_current)

        # Hanya tambahkan hasil jika ada gejala yang cocok
        if match_found:
            hasil_diagnosis.append((penyakit_data['name'], cf_combine))

    # Mengurutkan hasil berdasarkan nilai CF tertinggi
    hasil_diagnosis.sort(key=lambda x: x[1], reverse=True)
    return hasil_diagnosis

# Fungsi untuk memproses input user dari form
def process_user_input(form_data):
    gejala_user = {}
    for symptom_code in form_data:
        try:
            user_input = int(form_data[symptom_code])  # Pastikan nilai yang diterima adalah integer
            gejala_user[symptom_code] = get_user_cf(user_input)  # Ubah ke CF
        except ValueError:
            print(f"Invalid input for {symptom_code}: {form_data[symptom_code]}")
            gejala_user[symptom_code] = 0  # Jika input tidak valid, atur CF ke 0
    print("Gejala user:", gejala_user)  # Debugging untuk memastikan nilai gejala
    return gejala_user

@app.route('/')
def start():
    return render_template('start.html')

@app.route('/diagnosa', methods=['GET', 'POST'])
def index():
    knowledge_base = load_knowledge_base_from_file()
    if not knowledge_base:
        return "Error: File knowledge base tidak ditemukan atau kosong."

    symptoms = {}
    for penyakit_data in knowledge_base.values():
        for gejala_code, gejala_data in penyakit_data['symptoms'].items():
            if gejala_code not in symptoms:
                symptoms[gejala_code] = gejala_data['name']

    symptoms_list = list(symptoms.items())
    items_per_page = 10
    page = int(request.args.get('page', 1))
    start = (page - 1) * items_per_page
    end = start + items_per_page

    page_symptoms = symptoms_list[start:end]

    total_pages = len(symptoms_list) // items_per_page + (1 if len(symptoms_list) % items_per_page > 0 else 0)

    # if 'user_data' not in session:
    #     session['user_data'] = {}
        
    # if request.method == 'POST':
    #     form_data = request.form
    #     for key, value in form_data.items():
    #         session['user_data'][key] = value
    #     print("data yang disimpan di session:", session['user_data'])

    
    return render_template(
        'index.html',
        symptoms=page_symptoms,
        page=page,
        total_pages=total_pages,
        items_per_page=items_per_page
    )

# @app.route('/diagnose', methods=['POST'])
# def diagnose_route():
#     knowledge_base = load_knowledge_base_from_file()
#     if not knowledge_base:
#         return "Error: Tidak dapat memuat knowledge base."        
#     print("request from data:", request.form)
#     gejala_user = {}
#     for symptom_code in request.form:
#         try:
#             user_input = int(request.form[symptom_code])
#             gejala_user[symptom_code] = user_input  # Menyimpan CF yang dipilih
#         except ValueError:
#             gejala_user[symptom_code] = 0  # Jika input tidak valid
            
#     print("gejala yang dipilih oleh user", gejala_user)

#     return render_template('result.html', gejala_user=gejala_user)

@app.route('/diagnose', methods=['POST'])
def diagnose_route():
    knowledge_base = load_knowledge_base_from_file()
    if not knowledge_base:
        return "Error: Tidak dapat memuat knowledge base."

    # Gabungkan data dari session (data yang diterima dari halaman sebelumnya)
    gejala_user = {}
    previous_data = request.form.get('previous_data', '')  # Ambil data sebelumnya dari hidden field

    # Jika ada data sebelumnya, gabungkan dengan data yang baru
    if previous_data:
        gejala_user.update(eval(previous_data))  # Konversi string kembali ke dictionary

    # Proses data yang dikirimkan di halaman ini
    for symptom_code in request.form:
        if symptom_code != 'previous_data':  # Jangan proses hidden field
            try:
                user_input = int(request.form[symptom_code])
                gejala_user[symptom_code] = user_input  # Simpan CF yang dipilih
            except ValueError:
                gejala_user[symptom_code] = 0  # Jika input tidak valid

    print("Gejala yang dipilih oleh user:", gejala_user)

    return render_template('result.html', gejala_user=gejala_user)


if __name__ == '__main__':
    app.run(debug=True)