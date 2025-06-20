# Crie este novo arquivo: src/routes/clients.py
from sqlalchemy import or_
from flask import Blueprint, jsonify, request, session
from src.models.models import Client, Address, Contact, db
from src.routes.auth import login_required
from datetime import datetime


clients_bp = Blueprint('clients', __name__)

# --- ROTAS PARA CLIENTES ---

@clients_bp.route('/', methods=['GET'], strict_slashes=False)
@login_required
def get_clients():
    """Lista todos os clientes não excluídos."""
    try:
        clients = Client.query.filter(Client.deleted_at.is_(None)).order_by(Client.razao_social).all()
        return jsonify([client.to_dict() for client in clients]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/<int:client_id>', methods=['GET'], strict_slashes=False)
@login_required
def get_client(client_id):
    """Retorna os detalhes de um cliente específico."""
    try:
        client = Client.query.filter(Client.id == client_id, Client.deleted_at.is_(None)).first_or_404()
        return jsonify(client.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@clients_bp.route('/', methods=['POST'], strict_slashes=False)
@login_required
def create_client():
    """Cria um novo cliente, seu endereço principal e seu contato principal."""
    try:
        data = request.json
        if not data or not data.get('cnpj') or not data.get('razao_social'):
            return jsonify({'error': 'CNPJ e Razão Social são obrigatórios'}), 400

        sanitized_cnpj = ''.join(filter(str.isdigit, data.get('cnpj', '')))
        existing_client = Client.query.filter_by(cnpj=sanitized_cnpj).first()
        if existing_client:
            return jsonify({'error': 'CNPJ já cadastrado'}), 400

        new_client = Client(
            cnpj=sanitized_cnpj,
            razao_social=data.get('razao_social'),
            nome_fantasia=data.get('nome_fantasia'),
            state_registration=data.get('state_registration'),
            email=data.get('email'),
            phone=data.get('phone'),
            notes=data.get('notes')
        )
        db.session.add(new_client)
        db.session.flush()

        # --- INÍCIO DA CORREÇÃO ---
        # Garante que todos os campos de endereço sejam passados para o objeto Address
        if data.get('street') and data.get('city'):
            sanitized_zip_code = data.get('zip_code', '').replace('.', '').replace('-', '')
            
            new_address = Address(
                client_id=new_client.id,
                type='Comercial',
                street=data.get('street'),
                number=data.get('number'),
                complement=data.get('complement'),
                neighborhood=data.get('neighborhood'),
                city=data.get('city'),
                state=data.get('state'),
                zip_code=sanitized_zip_code,
                is_primary=True
            )
            db.session.add(new_address)
        # --- FIM DA CORREÇÃO ---

        if data.get('email') or data.get('phone'):
            new_contact = Contact(
                client_id=new_client.id,
                name=data.get('razao_social'),
                role='Principal',
                email=data.get('email'),
                phone=data.get('phone'),
                is_primary=True
            )
            db.session.add(new_contact)
        
        db.session.commit()
        return jsonify(new_client.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# Em src/routes/clients.py, adicione esta função no final do arquivo

@clients_bp.route('/by_cnpj/<string:cnpj_str>', methods=['GET'], strict_slashes=False)
@login_required
def find_client_by_cnpj(cnpj_str):
    """Busca um cliente pelo CNPJ."""
    try:
        sanitized_cnpj = ''.join(filter(str.isdigit, cnpj_str))
        client = Client.query.filter_by(cnpj=sanitized_cnpj, deleted_at=None).first()
        
        if client:
            return jsonify(client.to_dict()), 200
        else:
            # É importante retornar 404 para que o frontend saiba que precisa buscar na ReceitaWS
            return jsonify({'error': 'Cliente não encontrado na base de dados'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@clients_bp.route('/<int:client_id>', methods=['PUT'], strict_slashes=False)
@login_required
def update_client(client_id):
    """Atualiza um cliente existente."""
    try:
        client = Client.query.filter(Client.id == client_id, Client.deleted_at.is_(None)).first_or_404()
        data = request.json
        
        # --- INÍCIO DA CORREÇÃO ---
        # Se um novo CNPJ foi enviado, sanitiza e verifica a duplicidade
        if 'cnpj' in data and data['cnpj'] != client.cnpj:
            sanitized_cnpj = ''.join(filter(str.isdigit, data.get('cnpj', '')))
            existing_client = Client.query.filter(Client.id != client_id, Client.cnpj == sanitized_cnpj).first()
            if existing_client:
                return jsonify({'error': 'Este CNPJ já está em uso por outra empresa'}), 400
            client.cnpj = sanitized_cnpj
        # --- FIM DA CORREÇÃO ---

        client.razao_social = data.get('razao_social', client.razao_social)
        client.nome_fantasia = data.get('nome_fantasia', client.nome_fantasia)
        client.state_registration = data.get('state_registration', client.state_registration)
        client.email = data.get('email', client.email)
        client.phone = data.get('phone', client.phone)
        client.notes = data.get('notes', client.notes)

        db.session.commit()
        return jsonify(client.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/<int:client_id>', methods=['DELETE'], strict_slashes=False)
@login_required
def delete_client(client_id):
    """Faz o soft delete de um cliente."""
    try:
        client = Client.query.filter(Client.id == client_id, Client.deleted_at.is_(None)).first_or_404()
        client.deleted_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Cliente excluído com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- ROTAS PARA ENDEREÇOS E CONTATOS (ANINHADAS SOB O CLIENTE) ---

@clients_bp.route('/<int:client_id>/addresses', methods=['POST'], strict_slashes=False)
@login_required
def add_address_to_client(client_id):
    """Adiciona um novo endereço a um cliente."""
    try:
        client = Client.query.filter(Client.id == client_id, Client.deleted_at.is_(None)).first_or_404()
        data = request.json
        # Validação básica
        if not data or not data.get('street') or not data.get('city') or not data.get('state') or not data.get('zip_code'):
             return jsonify({'error': 'Campos de endereço incompletos'}), 400
        
        new_address = Address(
            client_id=client.id,
            type=data.get('type', 'Comercial'),
            street=data.get('street'),
            number=data.get('number'),
            complement=data.get('complement'),
            neighborhood=data.get('neighborhood'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code')
        )
        db.session.add(new_address)
        db.session.commit()
        return jsonify(new_address.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@clients_bp.route('/<int:client_id>/contacts', methods=['POST'], strict_slashes=False)
@login_required
def add_contact_to_client(client_id):
    """Adiciona um novo contato a um cliente."""
    try:
        client = Client.query.filter(Client.id == client_id, Client.deleted_at.is_(None)).first_or_404()
        data = request.json
        if not data or not data.get('name'):
            return jsonify({'error': 'Nome do contato é obrigatório'}), 400

        new_contact = Contact(
            client_id=client.id,
            name=data.get('name'),
            role=data.get('role'),
            email=data.get('email'),
            phone=data.get('phone')
        )
        db.session.add(new_contact)
        db.session.commit()
        return jsonify(new_contact.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/search', methods=['GET'], strict_slashes=False)
@login_required
def search_clients():
    """Busca clientes por nome ou razão social."""
    try:
        search_term = request.args.get('q', '').strip()
        
        # Só executa a busca se o termo tiver pelo menos 3 caracteres
        if len(search_term) < 3:
            return jsonify([]), 200

        # O operador ILIKE faz uma busca case-insensitive (não diferencia maiúsculas de minúsculas)
        # O '%' é um coringa que significa "qualquer sequência de caracteres"
        search_pattern = f"%{search_term}%"

        clients = Client.query.filter(
            Client.deleted_at.is_(None),
            or_(
                Client.razao_social.ilike(search_pattern),
                Client.nome_fantasia.ilike(search_pattern)
            )
        ).order_by(Client.razao_social).limit(10).all() # Limita a 10 resultados por performance

        return jsonify([client.to_dict() for client in clients]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500