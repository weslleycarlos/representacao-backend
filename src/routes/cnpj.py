from flask import Blueprint, jsonify, request
import requests

cnpj_bp = Blueprint('cnpj', __name__)

# Em src/routes/cnpj.py

@cnpj_bp.route('/consultar', methods=['POST'], strict_slashes=False)
def consultar_cnpj():
    """Consulta dados de CNPJ e retorna um objeto completo para o formulário."""
    try:
        data = request.json
        
        if not data or not data.get('cnpj'):
            return jsonify({'error': 'CNPJ é obrigatório'}), 400
        
        cnpj = data['cnpj'].replace('.', '').replace('/', '').replace('-', '')
        
        if len(cnpj) != 14 or not cnpj.isdigit():
            return jsonify({'error': 'CNPJ inválido'}), 400
        
        url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj}'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': 'Erro ao consultar CNPJ na API externa'}), response.status_code
        
        api_data = response.json()
        
        if api_data.get('status') == 'ERROR':
            return jsonify({'error': api_data.get('message', 'CNPJ não encontrado')}), 404
        
        # --- INÍCIO DA CORREÇÃO ---
        # Mapeia todos os campos necessários da resposta da API
        # para um novo objeto que será enviado ao frontend.
        formatted_response = {
            'cnpj': api_data.get('cnpj', ''),
            # A API da ReceitaWS usa 'nome' para Razão Social
            'razao_social': api_data.get('nome', ''),
            'nome_fantasia': api_data.get('fantasia', ''),
            'situacao': api_data.get('situacao', ''),
            'email': api_data.get('email', ''),
            'telefone': api_data.get('telefone', ''),
            'logradouro': api_data.get('logradouro', ''),
            'numero': api_data.get('numero', ''),
            'complemento': api_data.get('complemento', ''),
            'bairro': api_data.get('bairro', ''),
            'municipio': api_data.get('municipio', ''),
            'uf': api_data.get('uf', ''),
            'cep': api_data.get('cep', ''),
        }
        # --- FIM DA CORREÇÃO ---
        
        return jsonify(formatted_response), 200
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'A consulta ao CNPJ demorou muito para responder (timeout)'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Erro de conexão ao consultar CNPJ: {e}'}), 503
    except Exception as e:
        return jsonify({'error': f'Um erro inesperado ocorreu no servidor: {e}'}), 500

