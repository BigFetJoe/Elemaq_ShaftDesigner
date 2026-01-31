import numpy as np
import scipy as sp

# Resistencia a fadiga estimada
def K_fadiga(res_ult: float) -> float:
    """
    Estimativa da resistencia à fadiga (Se') baseada na tensão de ruptura (Sut).
    """
    if res_ult <= 1400.0e6: # Assuming Pascal input based on usage elsewhere, or adjust if MPa
        return 0.5 * res_ult
    else:
        return 700.0e6

# Fator de superficie (ka)
def K_acabamento(res_ult: float, acab_sup: str) -> float:
    """
    Calcula fator de acabamento superficial (ka).
    res_ult: Tensão de ruptura em Pa (será convertida para MPa para a fórmula).
    """
    acabamentoDict = {
        'retificado': [1.58, -0.085],
        'laminado a frio': [4.51, -0.265],
        'usinado': [4.51, -0.265],
        'laminado a quente': [57.7, -0.718],
        'forjado': [272.0, -0.995]
    }
    
    if acab_sup not in acabamentoDict:
        return 1.0
        
    # Formula expects MPa
    sut_mpa = res_ult / 1e6
    a, b = acabamentoDict[acab_sup]
    
    return a * pow(sut_mpa, b)

# Fator de tamanho (kb)
def K_tamanho(tipo_carga: str, diam: float) -> float:
    """
    Calcula fator de tamanho (kb).
    diam: Diâmetro em metros.
    """
    # Converter para mm
    de_mm = diam * 1000.0
    
    if tipo_carga not in ['flexão', 'torção']:
        # Para carga axial, kb = 1
        return 1.0

    # Limites baseados em Shigley
    if de_mm < 2.79:
        # Se muito pequeno, assume 1 ou usa o limite inferior
        return 1.24 * pow(2.79, -0.107) 
    elif 2.79 <= de_mm <= 51:
        return 1.24 * pow(de_mm, -0.107)
    elif 51.0 < de_mm <= 254.0:
        return 1.51 * pow(de_mm, -0.157)
    elif de_mm > 254.0:
        return 0.6 # Limite conservador para eixos grandes
        
    return 1.0

# Fator de carregamento (kc)
def K_carga(tipo_carga: str) -> float:
    kc = {
        'flexão': 1.0,
        'axial': 0.85,
        'torção': 0.59
    }
    return kc.get(tipo_carga, 1.0)

# Fator de temperatura (kd)
def K_temperatura(tc: float) -> float:
    """
    Calcula fator de temperatura (kd).
    tc: temperatura em °C
    """
    # Tabela aproximada
    k_table = {
        20: 1.0,
        50: 1.010,
        100: 1.020,
        150: 1.025,
        200: 1.020,
        250: 1.0,
        300: 0.975,
        350: 0.943,
        400: 0.900,
        450: 0.843,
        500: 0.768,
        550: 0.672,
        600: 0.549
    }
    
    if tc in k_table:
        return k_table[tc]
    
    # Aproximação polinomial para valores fora da tabela
    kd = 0.9877 + 0.6507e-3*tc - 0.3414e-5*tc**2 + 0.562e-8*tc**3 - 6.246e-12*tc**4
    
    # Trava limites físicos razoáveis
    if kd > 1.025: kd = 1.025 # max da tabela
    if kd < 0.1: kd = 0.1 # evitar negativo ou zero
    
    return kd

# Fator de confiabilidade (ke)
def K_conf(confiabilidade: str) -> float:
    k_conf = {
        '50%': 1.0,
        '90%': 0.897,
        '95%': 0.868,
        '99%': 0.814,
        '99.9%': 0.753,
        '99.99%': 0.702,
        '99.999%': 0.659,
        '99.9999%': 0.620
    }
    return k_conf.get(confiabilidade, 1.0) # Default 50%

def marin_eq(res_ult: float, se_est: float, acab_superficial: str, diam: float, tip_carga: str, temp: float, confiabilidade: str, kf_misc: float = 1.0) -> float:
    """
    Calcula o limite de resistência à fadiga corrigido (Se).
    """
    ka = K_acabamento(res_ult, acab_superficial)
    kb = K_tamanho(tip_carga, diam)
    kc = K_carga(tip_carga)
    kd = K_temperatura(temp)
    ke = K_conf(confiabilidade)
    
    # kf agora passado como argumento (misc factor)
    
    s_e = ka * kb * kc * kd * ke * kf_misc * se_est
    return s_e