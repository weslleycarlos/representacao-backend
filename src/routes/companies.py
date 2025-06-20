from flask import Blueprint, jsonify, request, session
from src.models.models import Company, db
from src.routes.auth import login_required
from datetime import datetime

companies_bp = Blueprint('companies', __name__)

@companies_bp.route('/', methods=['GET'],strict_slashes=False)
@login_required
def get_companies():
    """Lista todas as empresas cadastradas não excluídas."""
    try:
        companies = Company.query.filter(Company.deleted_at.is_(None)).order_by(Company.name).all()
        return jsonify([company.to_dict() for company in companies]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@companies_bp.route('/', methods=['POST'],strict_slashes=False)
@login_required
def create_company():
    """Cria uma nova empresa."""
    try:
        data = request.json
        if not data or not data.get('name') or not data.get('cnpj'):
            return jsonify({'error': 'Nome e CNPJ são obrigatórios'}), 400

        existing_company = Company.query.filter_by(cnpj=data['cnpj']).first()
        if existing_company:
            return jsonify({'error': 'CNPJ já cadastrado'}), 400

        new_company = Company(name=data['name'], cnpj=data['cnpj'])
        db.session.add(new_company)
        db.session.commit()

        return jsonify(new_company.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@companies_bp.route('/<int:company_id>', methods=['DELETE'],strict_slashes=False)
@login_required
def delete_company(company_id):
    """Faz o soft delete de uma empresa."""
    try:
        company = Company.query.get_or_404(company_id)
        
        # --- ALTERAÇÃO AQUI ---
        # Em vez de deletar, define a data de exclusão
        company.deleted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Empresa excluída com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@companies_bp.route('/<int:company_id>', methods=['PUT'],strict_slashes=False)
@login_required
def update_company(company_id):
    """Atualiza uma empresa existente."""
    try:
        company = Company.query.get_or_404(company_id)
        data = request.json

        if not data:
            return jsonify({'error': 'Dados são obrigatórios'}), 400

        # Verifica se o novo CNPJ já existe em outra empresa
        if 'cnpj' in data and data['cnpj'] != company.cnpj:
            existing_company = Company.query.filter_by(cnpj=data['cnpj']).first()
            if existing_company:
                return jsonify({'error': 'Este CNPJ já está em uso por outra empresa'}), 400
        
        company.name = data.get('name', company.name)
        company.cnpj = data.get('cnpj', company.cnpj)
        
        db.session.commit()
        return jsonify(company.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

