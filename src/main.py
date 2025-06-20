import os
import sys
from dotenv import load_dotenv
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.models.models import db
from src.routes.auth import auth_bp
from src.routes.dashboard import dashboard_bp
from src.routes.cnpj import cnpj_bp
from src.routes.orders import orders_bp
from src.routes.catalog import catalog_bp
from src.routes.companies import companies_bp
from src.routes.clients import clients_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

origins = [
    "http://localhost:5173", # Frontend de desenvolvimento local
    "https://representacao-frontend.onrender.com" # Frontend em produção
]

# Configuração CORS para permitir requisições do frontend
CORS(app, supports_credentials=True, origins=origins)

# Registra os blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(cnpj_bp, url_prefix='/api/cnpj')
app.register_blueprint(orders_bp, url_prefix='/api/orders')
app.register_blueprint(catalog_bp, url_prefix='/api/catalog')
app.register_blueprint(companies_bp, url_prefix='/api/companies')
app.register_blueprint(clients_bp, url_prefix='/api/clients')

# Configuração do banco de dados
# Em src/main.py

# Lê a string de conexão da variável de ambiente DATABASE_URL
# Se não encontrar, continua usando o banco de dados SQLite local como fallback.
database_uri = os.environ.get('DATABASE_URL')

# IMPORTANTE: Corrige o dialeto para compatibilidade com SQLAlchemy
if database_uri and database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_uri or f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Cria as tabelas do banco de dados
with app.app_context():
    db.create_all()
    
    # Adiciona dados iniciais se necessário
    from src.models.models import PaymentMethod, Company, User, UserCompany, Product
    
    # Verifica se já existem formas de pagamento
    if PaymentMethod.query.count() == 0:
        payment_methods = [
            PaymentMethod(name='Dinheiro'),
            PaymentMethod(name='Cartão de Crédito'),
            PaymentMethod(name='Cartão de Débito'),
            PaymentMethod(name='PIX'),
            PaymentMethod(name='Boleto'),
            PaymentMethod(name='Transferência Bancária')
        ]
        for method in payment_methods:
            db.session.add(method)
    
    # Cria empresa e usuário de exemplo se não existirem
    if User.query.count() == 0:
        # Cria empresa de exemplo
        company = Company(
            name='Empresa Exemplo Ltda',
            cnpj='12.345.678/0001-90'
        )
        db.session.add(company)
        db.session.flush()
        
        # Cria usuário de exemplo
        user = User(email='admin@exemplo.com')
        user.set_password('123456')
        db.session.add(user)
        db.session.flush()
        
        # Associa usuário à empresa
        user_company = UserCompany(user_id=user.id, company_id=company.id)
        db.session.add(user_company)
        
        # Adiciona alguns produtos de exemplo
        products = [
            Product(
                company_id=company.id,
                code='CAMISETA-001',
                description='Camiseta Básica Algodão',
                value=29.90,
                sizes=['P', 'M', 'G', 'GG']
            ),
            Product(
                company_id=company.id,
                code='CALCA-001',
                description='Calça Jeans Masculina',
                value=89.90,
                sizes=['38', '40', '42', '44', '46']
            ),
            Product(
                company_id=company.id,
                code='TENIS-001',
                description='Tênis Esportivo',
                value=159.90,
                sizes=['37', '38', '39', '40', '41', '42', '43']
            )
        ]
        for product in products:
            db.session.add(product)
    
    db.session.commit()

# Em src/main.py

# Em src/main.py

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # --- INÍCIO DA CORREÇÃO ---
    # Se a requisição for para um endpoint da API que não existe,
    # retorna um erro 404 em JSON em vez de servir o index.html.
    if path.startswith('api/'):
        return jsonify({'error': 'Endpoint não encontrado'}), 404
    # --- FIM DA CORREÇÃO ---

    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

