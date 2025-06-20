# Crie este novo arquivo: src/routes/users.py

from flask import Blueprint, jsonify, request
from src.models.models import User, Company, UserCompany, db
from src.routes.auth import login_required

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def get_users():
    """Lista todos os usuários do sistema."""
    try:
        users = User.query.order_by(User.full_name).all()
        return jsonify([user.to_dict() for user in users]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/', methods=['POST'], strict_slashes=False)
@login_required
def create_user():
    """Cria um novo usuário."""
    try:
        data = request.json
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Este email já está em uso'}), 400

        new_user = User(
            email=data['email'],
            full_name=data.get('full_name'),
            role=data.get('role', 'user')
        )
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<int:user_id>', methods=['GET'], strict_slashes=False)
@login_required
def get_user_details(user_id):
    """Retorna os detalhes de um usuário, incluindo suas empresas."""
    try:
        user = User.query.get_or_404(user_id)
        user_data = user.to_dict()
        
        # Pega as empresas associadas
        user_companies = db.session.query(Company).join(UserCompany).filter(UserCompany.user_id == user_id).all()
        user_data['companies'] = [company.to_dict() for company in user_companies]
        
        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@users_bp.route('/<int:user_id>', methods=['PUT'], strict_slashes=False)
@login_required
def update_user(user_id):
    """Atualiza os dados de um usuário."""
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        user.full_name = data.get('full_name', user.full_name)
        user.role = data.get('role', user.role)
        user.is_active = data.get('is_active', user.is_active)

        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email já está em uso'}), 400
            user.email = data['email']

        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<int:user_id>/companies', methods=['POST'], strict_slashes=False)
@login_required
def associate_company_to_user(user_id):
    """Associa uma empresa a um usuário."""
    try:
        data = request.json
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({'error': 'company_id é obrigatório'}), 400

        # Verifica se a associação já existe
        existing_link = UserCompany.query.filter_by(user_id=user_id, company_id=company_id).first()
        if existing_link:
            return jsonify({'message': 'Usuário já associado a esta empresa'}), 200

        new_link = UserCompany(user_id=user_id, company_id=company_id)
        db.session.add(new_link)
        db.session.commit()
        return jsonify({'message': 'Empresa associada com sucesso'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<int:user_id>/companies/<int:company_id>', methods=['DELETE'], strict_slashes=False)
@login_required
def disassociate_company_from_user(user_id, company_id):
    """Remove a associação de uma empresa de um usuário."""
    try:
        link = UserCompany.query.filter_by(user_id=user_id, company_id=company_id).first_or_404()
        db.session.delete(link)
        db.session.commit()
        return jsonify({'message': 'Associação removida com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500