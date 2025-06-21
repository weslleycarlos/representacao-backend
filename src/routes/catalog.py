from flask import Blueprint, jsonify, request, session
from src.models.models import Product, PaymentMethod, db
from src.routes.auth import login_required
from datetime import datetime
from sqlalchemy import and_, or_

catalog_bp = Blueprint('catalog', __name__)

@catalog_bp.route('/products', methods=['GET'], strict_slashes=False)
@login_required
def get_products():
    """Lista todos os produtos não excluídos da empresa selecionada, com filtro opcional por busca"""
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400

        # Obtém o parâmetro de busca, se fornecido
        search_query = request.args.get('search', '').strip()

        # Monta a query base
        query = Product.query.filter(
            and_(
                Product.company_id == company_id,
                Product.deleted_at.is_(None)
            )
        )

        # Adiciona filtro de busca, se houver
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Product.code.ilike(search_term),
                    Product.description.ilike(search_term)
                )
            )

        products = query.all()
        return jsonify([product.to_dict() for product in products]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@catalog_bp.route('/products/<int:product_id>', methods=['DELETE'], strict_slashes=False)
@login_required
def delete_product(product_id):
    """Faz o soft delete de um produto"""
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400

        product = Product.query.filter_by(id=product_id, company_id=company_id).first()
        if not product:
            return jsonify({'error': 'Produto não encontrado ou não pertence a esta empresa'}), 404

        product.deleted_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Produto excluído com sucesso'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@catalog_bp.route('/products', methods=['POST'])
@login_required
def create_product():
    """Cria um novo produto"""
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400

        data = request.json
        if not data:
            return jsonify({'error': 'Dados do produto são obrigatórios'}), 400

        required_fields = ['code', 'description', 'value']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400

        existing_product = Product.query.filter_by(
            company_id=company_id,
            code=data['code']
        ).first()

        if existing_product:
            return jsonify({'error': 'Código do produto já existe nesta empresa'}), 400

        product = Product(
            company_id=company_id,
            code=data['code'],
            description=data['description'],
            value=data['value'],
            sizes=data.get('sizes', [])
        )

        db.session.add(product)
        db.session.commit()

        return jsonify({
            'message': 'Produto criado com sucesso',
            'product': product.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@catalog_bp.route('/payment-methods', methods=['GET'], strict_slashes=False)
def get_payment_methods():
    """Lista todas as formas de pagamento ativas"""
    try:
        payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
        return jsonify([method.to_dict() for method in payment_methods]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@catalog_bp.route('/payment-methods', methods=['POST'], strict_slashes=False)
@login_required
def create_payment_method():
    """Cria uma nova forma de pagamento"""
    try:
        data = request.json
        if not data or not data.get('name'):
            return jsonify({'error': 'Nome da forma de pagamento é obrigatório'}), 400

        existing_method = PaymentMethod.query.filter_by(name=data['name']).first()
        if existing_method:
            return jsonify({'error': 'Forma de pagamento já existe'}), 400

        payment_method = PaymentMethod(
            name=data['name'],
            is_active=data.get('is_active', True)
        )

        db.session.add(payment_method)
        db.session.commit()

        return jsonify({
            'message': 'Forma de pagamento criada com sucesso',
            'payment_method': payment_method.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@catalog_bp.route('/products/<int:product_id>', methods=['PUT'], strict_slashes=False)
@login_required
def update_product(product_id):
    """Atualiza um produto existente"""
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400

        product = Product.query.filter_by(id=product_id, company_id=company_id).first()
        if not product:
            return jsonify({'error': 'Produto não encontrado ou não pertence a esta empresa'}), 404

        data = request.json
        if not data:
            return jsonify({'error': 'Dados do produto são obrigatórios'}), 400

        product.description = data.get('description', product.description)
        product.value = data.get('value', product.value)
        product.sizes = data.get('sizes', product.sizes)

        if 'code' in data and data['code'] != product.code:
            return jsonify({'error': 'O código do produto não pode ser alterado'}), 400

        db.session.commit()

        return jsonify({
            'message': 'Produto atualizado com sucesso',
            'product': product.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@catalog_bp.route('/products/by_code/<code>', methods=['GET'], strict_slashes=False)
@login_required
def get_product_by_code(code):
    """Busca um produto pelo código na empresa atual do usuário."""
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400

        product = Product.query.filter_by(
            company_id=company_id,
            code=code,
            deleted_at=None
        ).first()

        if product:
            return jsonify(product.to_dict()), 200
        else:
            return jsonify({'error': 'Produto não encontrado neste catálogo'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@catalog_bp.route('/import', methods=['POST'], strict_slashes=False)
@login_required
def import_products():
    """
    Importa uma lista de produtos.
    - Cria novos produtos se o código não existir.
    - Atualiza produtos existentes se o código já existir.
    - Desativa (soft delete) produtos do banco que não estão na planilha.
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Nenhuma empresa selecionada'}), 400

        incoming_products = request.json
        if not isinstance(incoming_products, list):
            return jsonify({'error': 'O corpo da requisição deve ser uma lista de produtos'}), 400

        existing_products_query = Product.query.filter_by(company_id=company_id).all()
        existing_products_map = {p.code: p for p in existing_products_query}

        incoming_product_codes = {item.get('code') for item in incoming_products if item.get('code')}

        created_count = 0
        updated_count = 0
        deactivated_count = 0

        for item in incoming_products:
            code = item.get('code')
            if not code:
                continue

            value = item.get('value')
            if value is None:
                continue

            product = existing_products_map.get(code)

            if product:
                product.description = item.get('description', product.description)
                product.value = value
                product.sizes = item.get('sizes', product.sizes)
                product.deleted_at = None
                updated_count += 1
            else:
                new_product = Product(
                    company_id=company_id,
                    code=code,
                    description=item.get('description'),
                    value=value,
                    sizes=item.get('sizes', [])
                )
                db.session.add(new_product)
                created_count += 1

        for code, product in existing_products_map.items():
            if code not in incoming_product_codes:
                if not product.deleted_at:
                    product.deleted_at = datetime.utcnow()
                    deactivated_count += 1

        db.session.commit()

        return jsonify({
            'message': 'Importação concluída com sucesso!',
            'created': created_count,
            'updated': updated_count,
            'deactivated': deactivated_count
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Um erro inesperado ocorreu: {str(e)}'}), 500