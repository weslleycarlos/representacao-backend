from flask import Blueprint, jsonify, request, session
from flask_login import login_user, logout_user, login_required, current_user
from src.models.models import User, Company, UserCompany, db
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorator para verificar se o usuário está logado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # --- INÍCIO DA ALTERAÇÃO ---
        # Permite que as requisições preflight (OPTIONS) passem sem verificação de login
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        # --- FIM DA ALTERAÇÃO ---
            
        if 'user_id' not in session:
            return jsonify({'error': 'Login necessário'}), 401
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registra um novo usuário"""
    try:
        data = request.json
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400
        
        # Verifica se o usuário já existe
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email já cadastrado'}), 400
        
        # Cria novo usuário
        user = User(email=data['email'])
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuário criado com sucesso',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Autentica um usuário"""
    try:
        data = request.json
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400
        
        # Busca o usuário
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Email ou senha inválidos'}), 401
        
        # Cria sessão
        session['user_id'] = user.id
        
        # Busca empresas do usuário
        user_companies = db.session.query(UserCompany, Company).join(
            Company, UserCompany.company_id == Company.id
        ).filter(UserCompany.user_id == user.id).all()
        
        companies = [company.to_dict() for _, company in user_companies]
        
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'companies': companies
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Faz logout do usuário"""
    session.pop('user_id', None)
    session.pop('company_id', None)
    return jsonify({'message': 'Logout realizado com sucesso'}), 200

@auth_bp.route('/select-company', methods=['POST'])
@login_required
def select_company():
    """Seleciona a empresa ativa para o usuário"""
    try:
        data = request.json
        
        if not data or not data.get('company_id'):
            return jsonify({'error': 'ID da empresa é obrigatório'}), 400
        
        # Verifica se o usuário tem acesso à empresa
        user_company = UserCompany.query.filter_by(
            user_id=session['user_id'],
            company_id=data['company_id']
        ).first()
        
        if not user_company:
            return jsonify({'error': 'Acesso negado à empresa'}), 403
        
        # Define a empresa ativa na sessão
        session['company_id'] = data['company_id']
        
        company = Company.query.get(data['company_id'])
        
        return jsonify({
            'message': 'Empresa selecionada com sucesso',
            'company': company.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Em src/routes/auth.py

@auth_bp.route("/companies", methods=["GET"])
@login_required
def get_user_companies():
    """Busca as empresas associadas ao usuário logado."""
    try:
        # 1. Busca o usuário a partir do ID armazenado na sessão
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Sessão inválida"}), 401

        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        companies_data = []
        
        # 2. Usa o nome correto do relacionamento ('user_companies') definido em models.py
        for user_company_link in user.user_companies:
            company = user_company_link.company
            if company:
                companies_data.append({
                    "id": company.id,
                    "name": company.name,
                    "cnpj": company.cnpj
                })
                
        return jsonify({"companies": companies_data}), 200

    except Exception as e:
        # Adiciona um bloco try-except para capturar outros erros inesperados
        return jsonify({'error': f"Um erro inesperado ocorreu: {str(e)}"}), 500


# Em src/routes/auth.py

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Retorna informações do usuário logado, incluindo sua permissão"""
    try:
        user = User.query.get(session['user_id'])
        
        response_data = {
            # user.to_dict() já inclui a 'role' graças à nossa alteração no models.py
            'user': user.to_dict(), 
            'company_id': session.get('company_id')
        }
        
        if session.get('company_id'):
            company = Company.query.get(session['company_id'])
            response_data['company'] = company.to_dict() if company else None
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

