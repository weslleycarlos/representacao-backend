from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    # --- NOVOS CAMPOS ---
    full_name = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user_companies = db.relationship('UserCompany', back_populates='user', cascade='all, delete-orphan')
    orders = db.relationship('Order', back_populates='user')

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'full_name': self.full_name,
            'phone_number': self.phone_number,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    # --- NOVOS CAMPOS ---
    state_registration = db.Column(db.String(20), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    # ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user_companies = db.relationship('UserCompany', back_populates='company', cascade='all, delete-orphan')
    products = db.relationship('Product', back_populates='company')
    orders = db.relationship('Order', back_populates='company')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cnpj': self.cnpj,
            'state_registration': self.state_registration,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'website': self.website,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class UserCompany(db.Model):
    __tablename__ = 'user_companies'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), primary_key=True)
    
    user = db.relationship('User', back_populates='user_companies')
    company = db.relationship('Company', back_populates='user_companies')

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    razao_social = db.Column(db.String(255), nullable=False)
    nome_fantasia = db.Column(db.String(255))
    # --- NOVOS CAMPOS ---
    state_registration = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    # ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    orders = db.relationship('Order', back_populates='client')
    # --- NOVOS RELACIONAMENTOS ---
    addresses = db.relationship('Address', back_populates='client', cascade='all, delete-orphan')
    contacts = db.relationship('Contact', back_populates='client', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'cnpj': self.cnpj,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'state_registration': self.state_registration,
            'email': self.email,
            'phone': self.phone,
            'notes': self.notes,
            'addresses': [address.to_dict() for address in self.addresses],
            'contacts': [contact.to_dict() for contact in self.contacts]
        }

# --- NOVOS MODELOS ---
class Address(db.Model):
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False) # 'Comercial', 'Entrega', 'Faturamento'
    street = db.Column(db.String(255), nullable=False)
    number = db.Column(db.String(20))
    complement = db.Column(db.String(100))
    neighborhood = db.Column(db.String(100))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    zip_code = db.Column(db.String(9), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship('Client', back_populates='addresses')

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'street': self.street,
            'number': self.number,
            'complement': self.complement,
            'neighborhood': self.neighborhood,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'is_primary': self.is_primary
        }

class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(100)) # Ex: 'Comprador'
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship('Client', back_populates='contacts')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'email': self.email,
            'phone': self.phone,
            'is_primary': self.is_primary
        }
# --- FIM DOS NOVOS MODELOS ---


class PaymentMethod(db.Model):
    # ... (sem alterações)
    __tablename__ = 'payment_methods'    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    orders = db.relationship('Order', back_populates='payment_method')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'is_active': self.is_active
        }

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    value = db.Column(db.Numeric(10, 2), nullable=False)
    sizes = db.Column(db.JSON)
    deleted_at = db.Column(db.DateTime, nullable=True) # <-- Garante que está aqui
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company = db.relationship('Company', back_populates='products')
    order_items = db.relationship('OrderItem', back_populates='product')
    
    __table_args__ = (db.UniqueConstraint('company_id', 'code', name='_company_code_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'code': self.code,
            'description': self.description,
            'value': float(self.value) if self.value is not None else 0,
            'sizes': self.sizes,
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    # --- NOVOS CAMPOS ---
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=True)
    billing_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=True)
    observations = db.Column(db.Text, nullable=True)
    # ---
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'))
    discount_percentage = db.Column(db.Numeric(5, 2), default=0.00)
    total_value = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pendente')
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', back_populates='orders')
    company = db.relationship('Company', back_populates='orders')
    client = db.relationship('Client', back_populates='orders')
    payment_method = db.relationship('PaymentMethod', back_populates='orders')
    order_items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    # --- NOVOS RELACIONAMENTOS ---
    shipping_address = db.relationship('Address', foreign_keys=[shipping_address_id])
    billing_address = db.relationship('Address', foreign_keys=[billing_address_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'client_id': self.client_id,
            'shipping_address_id': self.shipping_address_id,
            'billing_address_id': self.billing_address_id,
            'observations': self.observations,
            'payment_method_id': self.payment_method_id,
            'discount_percentage': float(self.discount_percentage),
            'total_value': float(self.total_value),
            'status': self.status,
            'order_date': self.order_date.isoformat(),
            'client': self.client.to_dict() if self.client else None,
            'items': [item.to_dict() for item in self.order_items]
        }

class OrderItem(db.Model):
    # ... (sem alterações)
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.JSON, nullable=False)
    unit_value = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    order = db.relationship('Order', back_populates='order_items')
    product = db.relationship('Product', back_populates='order_items')
    
    def to_dict(self):
         return {
            'id': self.id,
            'product_code': self.product.code,
            'product_description': self.product.description,
            'quantity': self.quantity,
            'unit_value': float(self.unit_value)
        }