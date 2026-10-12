import json, sys
base_dir = 'resultados/'
def unir(a, b, salida):
    A = json.load(open(base_dir + a, encoding='utf-8'))
    B = json.load(open(base_dir + b, encoding='utf-8'))
    for k in ('cfg', 'pasos', 'semillas', 'huellas_sha256', 'sumo'):
        assert A[k] == B[k], k
    assert not A['errores'] and not B['errores'], (A['errores'], B['errores'])
    A['por_estrategia']['difuso_fase_cal'] = B['por_estrategia']['difuso_fase']
    A['control_params_difuso_fase_cal'] = B['control_params']
    json.dump(A, open(base_dir + salida, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
unir(sys.argv[1], sys.argv[2], sys.argv[3])
print('ok', sys.argv[3])
