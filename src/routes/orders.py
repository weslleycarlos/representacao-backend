from flask import Blueprint, jsonify, request, session
from src.models.models import Order, OrderItem, Client, Product, PaymentMethod, db
from src.routes.auth import login_required
from sqlalchemy import and_
from decimal import Decimal

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/', methods=['GET'],strict_slashes=False)
@login_required
def get_orders():
    """Lista todos os pedidos do usuário na empresa selecionada"""
    try:
        user_id = session['user_id']
        company_id = session.get('company_id')
        
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400
        
        orders = Order.query.filter(
            and_(
                Order.user_id == user_id,
                Order.company_id == company_id
            )
        ).order_by(Order.order_date.desc()).all()
        
        return jsonify([order.to_dict() for order in orders]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/', methods=['POST'])
@login_required
def create_order():
    """Cria um novo pedido"""
    try:
        user_id = session['user_id']
        company_id = session.get('company_id')
        
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400
        
        data = request.json
        
        if not data:
            return jsonify({'error': 'Dados do pedido são obrigatórios'}), 400
        
        # Validações básicas
        required_fields = ['client_cnpj', 'client_razao_social', 'items']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} é obrigatório'}), 400
        
        if not data['items'] or len(data['items']) == 0:
            return jsonify({'error': 'Pelo menos um item é obrigatório'}), 400
        
        # Verifica se há pelo menos um item com quantidade > 0
        has_valid_item = False
        for item in data['items']:
            if item.get('quantity'):
                for size, qty in item['quantity'].items():
                    if qty > 0:
                        has_valid_item = True
                        break
            if has_valid_item:
                break
        
        if not has_valid_item:
            return jsonify({'error': 'Pelo menos um item deve ter quantidade maior que zero'}), 400
        
        # Busca ou cria o cliente
        client = Client.query.filter_by(cnpj=data['client_cnpj']).first()
        if not client:
            client = Client(
                cnpj=data['client_cnpj'],
                razao_social=data['client_razao_social'],
                nome_fantasia=data.get('client_nome_fantasia', '')
            )
            db.session.add(client)
            db.session.flush()  # Para obter o ID do cliente
        
        # Busca método de pagamento se fornecido
        payment_method_id = None
        if data.get('payment_method_id'):
            payment_method = PaymentMethod.query.get(data['payment_method_id'])
            if payment_method and payment_method.is_active:
                payment_method_id = payment_method.id
        
        # Calcula o valor total
        total_value = Decimal('0.00')
        order_items_data = []
        
        for item_data in data['items']:
            product = Product.query.filter_by(
                company_id=company_id,
                code=item_data['code']
            ).first()
            
            if not product:
                return jsonify({'error': f'Produto {item_data["code"]} não encontrado'}), 404
            
            # Calcula quantidade total do item
            item_total_qty = sum(item_data['quantity'].values())
            if item_total_qty > 0:
                item_value = Decimal(str(item_data.get('unit_value', product.value))) * item_total_qty
                total_value += item_value
                
                order_items_data.append({
                    'product': product,
                    'quantity': item_data['quantity'],
                    'unit_value': Decimal(str(item_data.get('unit_value', product.value)))
                })
        
        # Aplica desconto se fornecido
        discount_percentage = Decimal(str(data.get('discount_percentage', 0)))
        if discount_percentage > 0:
            discount_amount = total_value * (discount_percentage / 100)
            total_value -= discount_amount
        
        # Cria o pedido
        order = Order(
            user_id=user_id,
            company_id=company_id,
            client_id=client.id,
            payment_method_id=payment_method_id,
            discount_percentage=discount_percentage,
            total_value=total_value,
            status='Concluído'  # Pedidos criados via API são considerados concluídos
        )
        
        db.session.add(order)
        db.session.flush()  # Para obter o ID do pedido
        
        # Cria os itens do pedido
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data['product'].id,
                quantity=item_data['quantity'],
                unit_value=item_data['unit_value']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Recarrega o pedido com relacionamentos
        order = Order.query.get(order.id)
        
        return jsonify({
            'message': 'Pedido criado com sucesso',
            'order': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/<int:order_id>', methods=['GET'],strict_slashes=False)
@login_required
def get_order(order_id):
    """Busca um pedido específico"""
    try:
        user_id = session['user_id']
        company_id = session.get('company_id')
        
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400
        
        order = Order.query.filter(
            and_(
                Order.id == order_id,
                Order.user_id == user_id,
                Order.company_id == company_id
            )
        ).first()
        
        if not order:
            return jsonify({'error': 'Pedido não encontrado'}), 404
        
        return jsonify(order.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/sync', methods=['POST'])
@login_required
def sync_orders():
    """Sincroniza pedidos offline (recebe uma lista de pedidos para criar)"""
    try:
        user_id = session['user_id']
        company_id = session.get('company_id')
        
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400
        
        data = request.json
        
        if not data or not data.get('orders'):
            return jsonify({'error': 'Lista de pedidos é obrigatória'}), 400
        
        synced_orders = []
        failed_orders = []
        
        for order_data in data['orders']:
            try:
                # Reutiliza a lógica de criação de pedido
                # Validações básicas
                required_fields = ['client_cnpj', 'client_razao_social', 'items']
                valid = True
                for field in required_fields:
                    if not order_data.get(field):
                        valid = False
                        break
                
                if not valid or not order_data['items'] or len(order_data['items']) == 0:
                    failed_orders.append({
                        'order': order_data,
                        'error': 'Dados inválidos'
                    })
                    continue
                
                # Verifica se há pelo menos um item com quantidade > 0
                has_valid_item = False
                for item in order_data['items']:
                    if item.get('quantity'):
                        for size, qty in item['quantity'].items():
                            if qty > 0:
                                has_valid_item = True
                                break
                    if has_valid_item:
                        break
                
                if not has_valid_item:
                    failed_orders.append({
                        'order': order_data,
                        'error': 'Nenhum item com quantidade válida'
                    })
                    continue
                
                # Busca ou cria o cliente
                client = Client.query.filter_by(cnpj=order_data['client_cnpj']).first()
                if not client:
                    client = Client(
                        cnpj=order_data['client_cnpj'],
                        razao_social=order_data['client_razao_social'],
                        nome_fantasia=order_data.get('client_nome_fantasia', '')
                    )
                    db.session.add(client)
                    db.session.flush()
                
                # Busca método de pagamento se fornecido
                payment_method_id = None
                if order_data.get('payment_method_id'):
                    payment_method = PaymentMethod.query.get(order_data['payment_method_id'])
                    if payment_method and payment_method.is_active:
                        payment_method_id = payment_method.id
                
                # Calcula o valor total
                total_value = Decimal('0.00')
                order_items_data = []
                
                for item_data in order_data['items']:
                    product = Product.query.filter_by(
                        company_id=company_id,
                        code=item_data['code']
                    ).first()
                    
                    if not product:
                        raise Exception(f'Produto {item_data["code"]} não encontrado')
                    
                    # Calcula quantidade total do item
                    item_total_qty = sum(item_data['quantity'].values())
                    if item_total_qty > 0:
                        item_value = Decimal(str(item_data.get('unit_value', product.value))) * item_total_qty
                        total_value += item_value
                        
                        order_items_data.append({
                            'product': product,
                            'quantity': item_data['quantity'],
                            'unit_value': Decimal(str(item_data.get('unit_value', product.value)))
                        })
                
                # Aplica desconto se fornecido
                discount_percentage = Decimal(str(order_data.get('discount_percentage', 0)))
                if discount_percentage > 0:
                    discount_amount = total_value * (discount_percentage / 100)
                    total_value -= discount_amount
                
                # Cria o pedido
                order = Order(
                    user_id=user_id,
                    company_id=company_id,
                    client_id=client.id,
                    payment_method_id=payment_method_id,
                    discount_percentage=discount_percentage,
                    total_value=total_value,
                    status='Concluído'
                )
                
                db.session.add(order)
                db.session.flush()
                
                # Cria os itens do pedido
                for item_data in order_items_data:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item_data['product'].id,
                        quantity=item_data['quantity'],
                        unit_value=item_data['unit_value']
                    )
                    db.session.add(order_item)
                
                synced_orders.append(order.id)
                
            except Exception as e:
                failed_orders.append({
                    'order': order_data,
                    'error': str(e)
                })
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(synced_orders)} pedidos sincronizados com sucesso',
            'synced_count': len(synced_orders),
            'failed_count': len(failed_orders),
            'synced_orders': synced_orders,
            'failed_orders': failed_orders
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
    # Em src/routes/orders.py

# ... (outras importações e rotas existentes)

@orders_bp.route('/<int:order_id>', methods=['GET'], strict_slashes=False)
@login_required
def get_order_details(order_id):
    """Retorna os detalhes de um pedido específico."""
    try:
        # Garante que o pedido pertence à empresa selecionada na sessão
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Empresa não selecionada'}), 400

        order = db.session.query(Order).filter(
            Order.id == order_id,
            Order.company_id == company_id
        ).first()

        if not order:
            return jsonify({'error': 'Pedido não encontrado ou não pertence a esta empresa'}), 404

        # O método to_dict() que já temos no models.py vai serializar tudo que precisamos
        return jsonify(order.to_dict()), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

