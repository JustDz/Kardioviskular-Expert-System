def diagnose(gejala_user, knowledge_base):
    hasil_diagnosis = []
    for penyakit_code, penyakit_data in knowledge_base.items():
        cf_combine = 0.0
        for gejala, expert_cf in penyakit_data['symptoms'].items():
            user_cf = gejala_user.get(gejala, 0.0)
            cf_current = calculate_cf(user_cf, expert_cf['weight'])
            cf_combine = combine_cf(cf_combine, cf_current)
        hasil_diagnosis.append((penyakit_data['name'], cf_combine))
    hasil_diagnosis.sort(key=lambda x: x[1], reverse=True)
    return hasil_diagnosis