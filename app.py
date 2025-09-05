import os
from typing import Optional, Tuple, Dict, Any
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc
from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging
import hashlib
from functools import wraps # Importar wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

class Config:
    """Configuração base da aplicação"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///Formulario.db'

class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///Formulario.db'

# No arquivo app.py, modifique a classe Usuario:
class Usuario(db.Model):
    """Modelo para usuários do sistema"""
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(10), nullable=False, default='normal')  # 'normal' ou 'admin'
    criado_em = db.Column(db.DateTime, default=datetime.now, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, password):
        """Cria um hash da senha"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        """Verifica se a senha está correta"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def is_admin(self):
        """Verifica se o usuário é administrador"""
        return self.tipo == 'admin'

class Conta(db.Model):
    """Modelo para contas financeiras"""
    __tablename__ = 'contas'
    id = db.Column(db.Integer, primary_key=True)
    codigo_conta = db.Column(db.String(50), nullable=False, unique=True, index=True)
    descricao = db.Column(db.String(200), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.now, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f'<Conta {self.codigo_conta}>'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'codigo_conta': self.codigo_conta,
            'descricao': self.descricao,
            'criado_em': self.criado_em,
            'ativo': self.ativo
        }

class Saldo(db.Model):
    """Modelo para saldos das contas"""
    __tablename__ = 'saldos'
    valor = db.Column(db.Numeric(14, 2), nullable=False)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.String(8), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True, primary_key=True)
    
    descricao = db.Column(db.String(500))
    
    conta = db.relationship('Conta', backref=db.backref('saldos', lazy='dynamic'))

    def __repr__(self) -> str:
        return f'<Saldo da conta {self.conta_id} - {self.valor}>'

    @property
    def valor_formatado(self) -> str:
        return f"R$ {self.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

class DataValidator:
    @staticmethod
    def validate_amount(amount_str: str) -> Tuple[Optional[Decimal], Optional[str]]:
        if not amount_str or not amount_str.strip():
            return None, 'O campo Valor é obrigatório.'
        try:
            normalized = amount_str.strip().replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            if not any(char.isdigit() for char in normalized):
                 return None, 'Valor deve conter números.'
            amount_val = Decimal(normalized).quantize(Decimal('0.01'))

            if amount_val < Decimal('-999999999999.99') or amount_val > Decimal('999999999999.99'):
                return None, 'Valor fora do intervalo permitido.'
            return amount_val, None
        except (InvalidOperation, ValueError) as e:
            logger.warning(f"Erro na validação de valor: {amount_str} - {e}")
            return None, 'Formato de valor inválido. Use 1.234,56'

    @staticmethod
    def validate_account_code(code: str) -> Tuple[Optional[str], Optional[str]]:
        if not code or not code.strip():
            return None, 'O Código da conta é obrigatório.'
        code = code.strip().upper()
        if len(code) > 50:
            return None, 'Código da conta muito longo (máx 50 caracteres).'
        if not code.replace('-', '').replace('_', '').isalnum():
            return None, 'Código deve conter apenas letras, números, hífen e underscore.'
        return code, None

    @staticmethod
    def validate_description(description: str) -> Tuple[Optional[str], Optional[str]]:
        if not description or not description.strip():
            return None, 'A Descrição da conta é obrigatória.'
        description = description.strip()
        if len(description) > 200:
            return None, 'Descrição muito longa (máx 200 caracteres).'
        return description, None

class ContaService:
    @staticmethod
    def get_or_create_account(codigo_conta: str, descricao: str) -> Tuple[Optional[Conta], list]:
        errors = []
        code, code_error = DataValidator.validate_account_code(codigo_conta)
        if code_error:
            errors.append(code_error)

        desc, desc_error = DataValidator.validate_description(descricao)
        if desc_error:
            errors.append(desc_error)
        
        if errors:
            return None, errors

        existing_account = Conta.query.filter_by(codigo_conta=code).first()
        if existing_account:
            errors.append(f'Já existe uma conta com o código "{code}".')
            return None, errors

        try:
            conta = Conta(codigo_conta=code, descricao=desc)
            db.session.add(conta)
            db.session.flush()
            return conta, []
        except Exception as e:
            logger.error(f"Erro ao criar conta: {e}")
            db.session.rollback()
            return None, ['Erro interno ao processar a conta.']

class SaldoService:
    @staticmethod
    def create_saldo(conta: Conta, valor: Decimal, descricao: str = None) -> Tuple[bool, list]:
        try:
            now = datetime.now().replace(microsecond=0)
            
            saldo = Saldo(
                valor=valor,
                conta_id=conta.id,
                descricao=descricao,
                data=now.date(),
                hora=now.strftime('%H:%M:%S'),
                criado_em=now
            )
            db.session.add(saldo)
            db.session.commit()
            logger.info(f"Saldo criado: {valor} para conta {conta.codigo_conta}")
            return True, []
        except Exception as e:
            logger.error(f"Erro ao criar saldo: {e}")
            db.session.rollback()
            return False, ['Erro interno ao salvar o saldo.']

    @staticmethod
    def get_paginated_saldos(page: int = 1, per_page: int = 20):
        return (Saldo.query
                .join(Conta)
                .filter(Conta.ativo == True)
                .order_by(desc(Saldo.data), desc(Saldo.hora), desc(Saldo.criado_em))
                .paginate(page=page, per_page=per_page, error_out=False))

def login_required(f):
    """Decorator para verificar se o usuário está logado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para verificar se o usuário é admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        user = Usuario.query.get(session['user_id'])
        if not user or not user.is_admin():
            flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function

def create_app(config_name: str = 'development') -> Flask:
    app = Flask(__name__)
    config_mapping = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    app.config.from_object(config_mapping.get(config_name, DevelopmentConfig))

    db.init_app(app)

    # No arquivo app.py, atualize a rota de login:

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # Se o usuário já está logado, redireciona para a página inicial
        if 'user_id' in session:
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            # Verificar credenciais no banco de dados
            usuario = Usuario.query.filter_by(username=username, ativo=True).first()
            
            if usuario and usuario.check_password(password):
                session['user_id'] = usuario.id
                session['username'] = usuario.username
                session['user_type'] = usuario.tipo
                flash('Login realizado com sucesso!', 'success')
                
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Usuário ou senha incorretos.', 'danger')
        
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Você foi desconectado com sucesso.', 'info')
        return redirect(url_for('login'))
    
    @app.route('/')
    @login_required
    def index():
        # Buscar todas as contas ativas com seus saldos
        contas = Conta.query.filter_by(ativo=True).order_by(Conta.codigo_conta).all()
        contas_com_saldos = []

        for conta in contas:
            # Pegar todos os saldos da conta ordenados do mais recente para o mais antigo
            saldos_ordenados = (Saldo.query
                            .filter_by(conta_id=conta.id)
                            .order_by(desc(Saldo.data), desc(Saldo.hora), desc(Saldo.criado_em))
                            .all())
            
            if saldos_ordenados:
                saldo_atual = saldos_ordenados[0]
                ultimos_saldos = saldos_ordenados[1:] if len(saldos_ordenados) > 1 else []
                
                # Formatar últimos saldos apenas com valores (sem data)
                ultimos_saldos_formatados = []
                for saldo in ultimos_saldos:
                    valor_formatado = f"R$ {saldo.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    ultimos_saldos_formatados.append(valor_formatado)
                
                # Adicionar propriedades ao objeto conta
                conta.saldo_atual = saldo_atual.valor_formatado
                conta.ultimos_saldos = ', '.join(ultimos_saldos_formatados) if ultimos_saldos_formatados else 'Nenhum registro anterior'
            else:
                # Conta sem saldos
                conta.saldo_atual = 'R$ 0,00'
                conta.ultimos_saldos = 'Nenhum registro anterior'
                
            contas_com_saldos.append(conta)

        return render_template('index.html', contas=contas_com_saldos)

    # No arquivo app.py, adicione a seguinte rota após a rota de login:

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        # Se o usuário já está logado, redireciona para a página inicial
        if 'user_id' in session:
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            # Removido: tipo = request.form.get('tipo', 'normal').strip()
            
            # Validações
            errors = []
            
            if not username:
                errors.append('O nome de usuário é obrigatório.')
            elif len(username) < 3:
                errors.append('O nome de usuário deve ter pelo menos 3 caracteres.')
            elif Usuario.query.filter_by(username=username).first():
                errors.append('Este nome de usuário já está em uso.')
                
            if not password:
                errors.append('A senha é obrigatória.')
            elif len(password) < 6:
                errors.append('A senha deve ter pelo menos 6 caracteres.')
            elif password != confirm_password:
                errors.append('As senhas não coincidem.')
                
            # Removida a validação de 'tipo'
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('register.html')
            
            try:
                # Criar novo usuário sempre como 'normal'
                novo_usuario = Usuario(
                    username=username,
                    tipo='normal',  # Define o tipo como 'normal' diretamente
                    ativo=True
                )
                novo_usuario.set_password(password)
                
                db.session.add(novo_usuario)
                db.session.commit()
                
                flash('Conta criada com sucesso! Faça login para continuar.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                logger.error(f"Erro ao criar usuário: {e}")
                db.session.rollback()
                flash('Erro interno ao criar a conta. Tente novamente.', 'danger')
        
        return render_template('register.html')
    
    @app.route('/novo')
    @login_required
    def novo():
        contas = Conta.query.filter_by(ativo=True).order_by(Conta.codigo_conta).all()
        return render_template('form.html', contas=contas, old=request.args.get('old'))

    @app.route('/salvar', methods=['POST'])
    @login_required
    def salvar():
        mode = request.form.get('account_mode', 'existing')
        selected_conta_id = request.form.get('conta_id')
        codigo_conta = request.form.get('codigo_conta', '').strip()
        descricao = request.form.get('descricao', '').strip()
        valor_raw = request.form.get('amount', '').strip()
        saldo_descricao = request.form.get('balance_description', '').strip()

        errors = []
        conta = None
        
        valor_val, amount_error = DataValidator.validate_amount(valor_raw)
        if amount_error:
            errors.append(amount_error)

        if mode == 'existing':
            if not selected_conta_id:
                errors.append('Selecione uma conta existente.')
            else:
                try:
                    conta = Conta.query.get(int(selected_conta_id))
                    if not conta or not conta.ativo:
                        errors.append('Conta selecionada é inválida ou inativa.')
                except (ValueError, TypeError):
                    errors.append('ID de conta inválido.')
        elif mode == 'new':
            conta, conta_errors = ContaService.get_or_create_account(codigo_conta, descricao)
            if conta_errors:
                errors.extend(conta_errors)
        else:
            errors.append('Modo de seleção de conta inválido.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            
            old_data = {
                'account_mode': mode, 'conta_id': selected_conta_id,
                'codigo_conta': codigo_conta, 'descricao': descricao,
                'amount': valor_raw, 'balance_description': saldo_descricao
            }
            contas = Conta.query.filter_by(ativo=True).order_by(Conta.codigo_conta).all()
            return render_template('form.html', contas=contas, old=old_data)

        success, saldo_errors = SaldoService.create_saldo(
            conta, valor_val, saldo_descricao or None
        )
        
        if success:
            formatted_amount = f"R$ {valor_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            flash(f'Saldo de {formatted_amount} salvo com sucesso para a conta {conta.codigo_conta}!', 'success')
            return redirect(url_for('index'))
        else:
            for error in saldo_errors:
                flash(error, 'danger')
            return redirect(url_for('novo'))

    # NOVA ROTA PARA ADICIONAR SALDO VIA MODAL
    @app.route('/adicionar_saldo', methods=['POST'])
    @login_required
    def adicionar_saldo():
        """Rota para adicionar novo saldo a uma conta específica via modal"""
        try:
            conta_id = request.form.get('conta_id')
            valor_raw = request.form.get('amount', '').strip()
            saldo_descricao = request.form.get('balance_description', '').strip()

            # Validar ID da conta
            if not conta_id:
                flash('Erro: ID da conta não informado.', 'danger')
                return redirect(url_for('index'))

            try:
                conta = Conta.query.get(int(conta_id))
                if not conta or not conta.ativo:
                    flash('Erro: Conta não encontrada ou inativa.', 'danger')
                    return redirect(url_for('index'))
            except (ValueError, TypeError):
                flash('Erro: ID de conta inválido.', 'danger')
                return redirect(url_for('index'))

            # Validar valor
            valor_val, amount_error = DataValidator.validate_amount(valor_raw)
            if amount_error:
                flash(f'Erro no valor: {amount_error}', 'danger')
                return redirect(url_for('index'))

            # Criar o novo saldo
            success, saldo_errors = SaldoService.create_saldo(
                conta, valor_val, saldo_descricao or None
            )

            if success:
                formatted_amount = f"R$ {valor_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                flash(f'Novo saldo de {formatted_amount} adicionado com sucesso para a conta {conta.codigo_conta}!', 'success')
                logger.info(f"Novo saldo adicionado via modal - Conta: {conta.codigo_conta}, Valor: {valor_val}")
            else:
                for error in saldo_errors:
                    flash(f'Erro ao salvar: {error}', 'danger')

        except Exception as e:
            logger.error(f"Erro inesperado ao adicionar saldo: {e}")
            flash('Erro inesperado. Tente novamente.', 'danger')
            db.session.rollback()

        return redirect(url_for('index'))

    @app.route('/admin/usuarios')
    @admin_required
    def admin_usuarios():
        usuarios = Usuario.query.order_by(Usuario.username).all()
        return render_template('admin_users.html', usuarios=usuarios)

    # ROTA PARA PROMOVER USUÁRIO A ADMIN
    @app.route('/admin/promover_usuario', methods=['POST'])
    @admin_required
    def promover_usuario():
        user_id_to_promote = request.form.get('user_id')

        if not user_id_to_promote:
            flash('ID de usuário não fornecido.', 'danger')
            return redirect(url_for('admin_usuarios'))

        user_to_promote = Usuario.query.get(user_id_to_promote)

        if not user_to_promote:
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('admin_usuarios'))

        if user_to_promote.is_admin():
            flash(f'O usuário {user_to_promote.username} já é um administrador.', 'warning')
            return redirect(url_for('admin_usuarios'))

        try:
            user_to_promote.tipo = 'admin'
            db.session.commit()
            flash(f'Usuário {user_to_promote.username} promovido a administrador com sucesso!', 'success')
            current_user = Usuario.query.get(session['user_id'])
            logger.info(f"Usuário '{current_user.username}' promoveu '{user_to_promote.username}' para admin.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao promover usuário {user_to_promote.id}: {e}")
            flash('Ocorreu um erro ao promover o usuário. Tente novamente.', 'danger')

        return redirect(url_for('admin_usuarios'))

    @app.route('/admin/excluir_usuario', methods=['POST'])
    @admin_required
    def excluir_usuario():
        user_id = request.form.get('user_id')
        
        if not user_id:
            flash('ID de usuário não fornecido.', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        # Verificar se o usuário está tentando excluir a si mesmo
        if int(user_id) == session['user_id']:
            flash('Você não pode excluir sua própria conta.', 'danger')
            return redirect(url_for('admin_usuarios'))
        
        usuario_a_excluir = Usuario.query.get(user_id)
        if usuario_a_excluir:
            try:
                db.session.delete(usuario_a_excluir)
                db.session.commit()
                flash(f'Usuário {usuario_a_excluir.username} excluído com sucesso.', 'success')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao excluir usuário {usuario_a_excluir.id}: {e}")
                flash('Ocorreu um erro ao excluir o usuário.', 'danger')
        else:
            flash('Usuário não encontrado.', 'danger')
        
        return redirect(url_for('admin_usuarios'))

    @app.route('/conta/<int:conta_id>')
    @login_required
    def ver_conta(conta_id: int):
        conta = Conta.query.filter_by(id=conta_id, ativo=True).first_or_404()
        page = request.args.get('page', 1, type=int)
        pagination = (Saldo.query
                      .filter_by(conta_id=conta_id)
                      .order_by(desc(Saldo.data), desc(Saldo.hora))
                      .paginate(page=page, per_page=20, error_out=False))
        return render_template('account_detail.html', conta=conta, pagination=pagination, saldos=pagination.items)

    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    return app

def init_db(app: Flask):
    with app.app_context():
        db.create_all()
        
        # Criar usuário admin padrão se não existir
        if not Usuario.query.filter_by(username='admin').first():
            usuario = Usuario(username='admin', tipo='admin', ativo=True)
            # --- ALTERAÇÃO DA SENHA AQUI ---
            usuario.set_password('Nutrane@123') #
            db.session.add(usuario)
            db.session.commit()
            # --- ATUALIZAÇÃO DA MENSAGEM DE LOG ---
            logger.info("Usuário admin padrão criado: admin/Nutrane@123")
            
        logger.info("Banco de dados inicializado.")

if __name__ == '__main__':
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(env)
    init_db(app)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)