# ARQUIVO: app/routes/auth.py (Completo)

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from app.models.user import User, SiteSettings
from app.services.validation_service import verify_dentist_credentials, log_event
from markupsafe import Markup
from app.extensions import db
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

auth = Blueprint('auth', __name__)

# --- Formulário de Cadastro ---
class RegistrationForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired(message="Este campo é obrigatório.")])
    genero = SelectField('Gênero', choices=[('', 'Selecione...'), ('Masculino', 'Masculino'), ('Feminino', 'Feminino'), ('Outro', 'Outro')], validators=[DataRequired(message="Selecione um gênero.")])
    cro = StringField('Número do CRO', validators=[DataRequired(message="Este campo é obrigatório.")])
    uf_cro = SelectField('UF do CRO', choices=[('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'),('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'),('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'),('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'),('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')], validators=[DataRequired(message="Este campo é obrigatório.")])
    email = StringField('E-mail', validators=[DataRequired(message="Este campo é obrigatório."), Email(message="Por favor, insira um e-mail válido.")])
    whatsapp = StringField('WhatsApp (com DDD)', validators=[DataRequired(message="Este campo é obrigatório."), Length(min=10, message="Número de WhatsApp inválido.")])
    cpf = StringField('CPF', validators=[DataRequired(message="Este campo é obrigatório.")])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired(message="Selecione sua data de nascimento.")])
    password = PasswordField('Senha', validators=[DataRequired(message="Este campo é obrigatório."), Length(min=8, message="A senha deve ter no mínimo 8 caracteres.")])
    password2 = PasswordField('Confirme a Senha', validators=[DataRequired(message="Este campo é obrigatório."), EqualTo('password', message='As senhas devem ser iguais.')])
    accept_terms = BooleanField('Li e aceito os termos', validators=[DataRequired(message="Você deve aceitar os termos para se cadastrar.")])
    submit = SubmitField('Finalizar Cadastro')

class ForgotPasswordForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar Link de Recuperação')

# --- Rotas ---
@auth.route('/')
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    video_setting = SiteSettings.query.filter_by(key='login_video_url').first()
    video_url = video_setting.value if video_setting else "https://www.youtube.com/embed/Z0u9_xUv0ms"
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.dashboard'))
        else:
            flash('Login falhou. Verifique seu e-mail e senha.', 'danger')
            return redirect(url_for('auth.login'))
        
    return render_template('login.html', video_url=video_url)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    video_setting = SiteSettings.query.filter_by(key='login_video_url').first()
    video_url = video_setting.value if video_setting else "https://www.youtube.com/embed/Z0u9_xUv0ms"

    if request.method == 'POST':
        # --- LÓGICA DE VERIFICAÇÃO DE DUPLICIDADE ---
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        cro = request.form.get('cro')
        whatsapp = request.form.get('whatsapp') # <-- 1. ADICIONADO AQUI

        user_by_email = User.query.filter_by(email=email).first()
        user_by_cpf = User.query.filter_by(cpf=cpf).first()
        user_by_cro = User.query.filter_by(cro=cro).first()
        user_by_whatsapp = User.query.filter_by(whatsapp=whatsapp).first() # <-- 2. ADICIONADO AQUI

        error_message = None
        if user_by_email:
            error_message = "Este e-mail já está cadastrado."
        elif user_by_cpf:
            error_message = "Este CPF já está cadastrado."
        elif user_by_cro:
            error_message = "Este CRO já está cadastrado."
        elif user_by_whatsapp: # <-- 3. ADICIONADO AQUI
            error_message = "Este número de WhatsApp já está cadastrado."

        if error_message:
            # Cria a mensagem com um link para a recuperação de senha
            recovery_link = url_for('auth.forgot_password')
            full_message = Markup(f'{error_message} Se você já possui uma conta, <a href="{recovery_link}" class="font-bold underline">clique aqui para recuperar sua senha.</a>')
            flash(full_message, 'danger')
            return redirect(url_for('auth.register'))
        # --- FIM DA LÓGICA DE VERIFICAÇÃO ---

        if form.validate_on_submit():
            # Chama o novo serviço de validação
            success, message, report_details = verify_dentist_credentials(
                cpf=form.cpf.data,
                cro=form.cro.data,
                uf_cro=form.uf_cro.data,
                nome_completo=form.nome_completo.data,
                ip_address=request.remote_addr
            )

            if not success:
                flash(f'Falha na validação: {message}', 'danger')
                return render_template('register.html', form=form, video_url=video_url)

            # Se a validação foi bem-sucedida, cria o usuário
            user = User(
                nome_completo=form.nome_completo.data, email=form.email.data,
                cpf=form.cpf.data, cro=form.cro.data, uf_cro=form.uf_cro.data,
                whatsapp=form.whatsapp.data, data_nascimento=form.data_nascimento.data,
                genero=form.genero.data, ip_address=request.remote_addr
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            # Salva o relatório na sessão do usuário para uso posterior, se necessário
            session['validation_report'] = report_details
            
            # Redireciona para a tela de login
            flash('Cadastro validado com sucesso! Por favor, faça o login para continuar.', 'success')
            return redirect(url_for('auth.login'))
        
    # Se o formulário não for válido ou for um GET, renderiza a página com os erros
    return render_template('register.html', form=form, video_url=video_url)

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # SIMULAÇÃO
            token = "TOKEN_DE_RECUPERACAO_SIMULADO_12345"
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            print(f"--- SIMULAÇÃO DE ENVIO DE E-MAIL ---\nPara: {user.email}\nLink: {reset_link}\n------------------------------------")
            flash('Um link de recuperação foi "enviado" para seu e-mail (verifique o terminal).', 'info')
        else:
            flash('E-mail não encontrado em nosso sistema.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html', form=form)

@auth.route('/reset-password/<token>')
def reset_password(token):
    flash(f'Você chegou à página de reset com o token: {token}. Aqui você colocaria uma nova senha.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
