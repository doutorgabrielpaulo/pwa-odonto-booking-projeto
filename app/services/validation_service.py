import os
import requests
import json
from datetime import datetime
from app import db
from app.models.user import ApiLog

def log_event(event_type, status, details, user_id=None, ip_address=None):
    """Função central para criar entradas no Templog."""
    try:
        log_entry = ApiLog(
            event_type=event_type,
            status=status,
            details=json.dumps(details, ensure_ascii=False),
            user_id=user_id,
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"ERRO AO SALVAR LOG: {e}")
        db.session.rollback()

def verify_dentist_credentials(cpf: str, cro: str, uf_cro: str, nome_completo: str, ip_address: str) -> (bool, str, dict):
    """
    Verifica as credenciais, compara nomes de múltiplas fontes e gera dados para o relatório.
    Retorna: (sucesso, mensagem_para_usuario, dados_do_relatorio)
    """
    SIMULATION_MODE = False

    if SIMULATION_MODE:
        print("MODO DE SIMULAÇÃO: Validando credenciais...")
        # Simula o retorno das APIs
        cro_api_return = {"nome": nome_completo, "status": "Ativo"}
        cpf_api_return = {"nome": nome_completo, "situacao": "Regular"}

        # DEBUG: Imprime os dados simulados das APIs no terminal
        print(f"DEBUG: Retorno simulado da API do CRO: {cro_api_return}")
        print(f"DEBUG: Retorno simulado da API do CPF: {cpf_api_return}")

        if cro_api_return["nome"].strip().lower() == cpf_api_return["nome"].strip().lower():
            validation_status = "SUCESSO"
            message = "Validação cruzada de dados realizada com sucesso."
            success = True
        else:
            validation_status = "FALHA"
            message = "Os nomes retornados pelas consultas de CRO e CPF não coincidem."
            success = False
        
        report_details = {
            "validation_date": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
            "ip_address": ip_address,
            "cro_status": cro_api_return["status"],
            "cpf_status": cpf_api_return["situacao"],
            "name_check": "Nomes Coincidentes" if success else "Nomes Divergentes",
            "api_source": "Simulação InfoSimples"
        }
        
        log_event(
            event_type="Validação de Cadastro (Simulação)",
            status=validation_status,
            details=report_details,
            ip_address=ip_address
        )
        print("Cadastro realizado com sucesso.")
        return success, message, report_details

    # Lógica da API real (não simulada)
    # Aqui, você pode adicionar a mesma lógica de print() para depurar a resposta real.
    token = os.environ.get('INFOSIMPLES_API_TOKEN')
    if not token:
        return False, "Token da API InfoSimples não configurado no servidor.", {}

    # Lógica da API real para CRO
    url_cro = "https://api.infosimples.com/api/v2/consultas/conselho-federal-odontologia/cfo"
    params_cro = {"token": token, "numero_inscricao": cro, "uf": uf_cro, "timeout": 300}
    try:
        response_cro = requests.post(url_cro, data=params_cro)
        response_cro.raise_for_status()
        data_cro = response_cro.json()
        
        # DEBUG: Imprime a resposta real da API do CRO
        print(f"DEBUG: Resposta real da API do CRO: {data_cro}")

        if data_cro.get("code") != 200 or not data_cro.get("data"):
            return False, data_cro.get("code_message", "CRO ou UF inválidos."), {}
        nome_cro = data_cro.get("data")[0].get("nome", "")
    except requests.exceptions.RequestException as e:
        return False, "Não foi possível conectar ao serviço do CRO.", {}

    # Lógica da API real para CPF (simulada, pois a API real de CPF não está no código)
    # Supondo que exista uma API de CPF, você faria uma chamada similar aqui.
    url_cpf = "https://api.infosimples.com/api/v2/consultas/receita-federal/cpf"
    params_cpf = {"token": token, "cpf": cpf, "timeout": 300}
    try:
        response_cpf = requests.post(url_cpf, data=params_cpf)
        response_cpf.raise_for_status()
        data_cpf = response_cpf.json()

        # DEBUG: Imprime a resposta real da API do CPF
        print(f"DEBUG: Resposta real da API do CPF: {data_cpf}")

        if data_cpf.get("code") != 200 or not data_cpf.get("data"):
            return False, data_cpf.get("code_message", "CPF inválido."), {}
        nome_cpf = data_cpf.get("data")[0].get("nome", "")
    except requests.exceptions.RequestException as e:
        return False, "Não foi possível conectar ao serviço da Receita Federal.", {}

    # Compara os nomes retornados pelas APIs reais
    if nome_cro.strip().lower() == nome_cpf.strip().lower():
        message = "Validação cruzada de dados realizada com sucesso."
        success = True
    else:
        message = "Os nomes retornados pelas consultas de CRO e CPF não coincidem."
        success = False

    report_details = {
        "validation_date": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
        "ip_address": ip_address,
        "cro_status": data_cro.get("data")[0].get("situacao_inscricao", ""),
        "cpf_status": data_cpf.get("data")[0].get("situacao_cadastral", ""),
        "name_check": "Nomes Coincidentes" if success else "Nomes Divergentes",
        "api_source": "InfoSimples"
    }

    status = "SUCESSO" if success else "FALHA"
    log_event(
        event_type="Validação de Cadastro (API Real)",
        status=status,
        details=report_details,
        ip_address=ip_address
    )
    print("Cadastro realizado com sucesso.")
    return success, message, report_details
