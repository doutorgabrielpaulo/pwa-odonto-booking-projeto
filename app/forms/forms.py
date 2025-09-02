from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField, FloatField, TextAreaField, SelectField, TimeField, DateField
from wtforms.validators import DataRequired, Email, Optional, URL
from wtforms_sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

# Formulário para editar usuário
class AdminEditUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    score = IntegerField('Score')
    is_vip = BooleanField('Usuário VIP')
    is_chato = BooleanField('Usuário "Chato"')
    submit = SubmitField('Salvar Alterações')

# Formulário para criar/editar sala (cadeira)
class RoomForm(FlaskForm):
    name = StringField('Nome da Cadeira/Sala', validators=[DataRequired()])
    description = StringField('Descrição (Ex: Sala 122 - 12° andar torre A)', validators=[DataRequired()])
    price_2h30 = FloatField('Preço 2h30', validators=[DataRequired()])
    price_1h15 = FloatField('Preço 1h15', validators=[DataRequired()])
    allow_1h15_rental = BooleanField('Disponível para alugar 1h15', default=True)
    is_visible = BooleanField('Cadeira visível para os usuários', default=True)
    video_url = StringField('URL do Vídeo Demonstrativo (YouTube)', validators=[Optional(), URL()])
    video_tutorial_url = StringField('URL do Vídeo Tutorial (YouTube)', validators=[Optional(), URL()])
    video_tutorial_autoclave_url = StringField('URL do Vídeo Tutorial Autoclave (YouTube)', validators=[Optional(), URL()])
    video_tutorial_raiox_url = StringField('URL do Vídeo Tutorial Raiox (YouTube)', validators=[Optional(), URL()])
    video_tutorial_plastificadora_url = StringField('URL do Vídeo Tutorial Plastificadora (YouTube)', validators=[Optional(), URL()])
    admin_notice = TextAreaField('Aviso do Admin (Opcional)')
    
    # Tags pré-definidas como checkboxes
    standard_tags = [
        ('raiox', 'Raiox'),
        ('Fotopolimerizador', 'Fotopolimerizador'),
        ('autoclave', 'Autoclave'),
        ('bomba de vácuo', 'Bomba de vácuo'),
        ('ringlight 18"', 'Ringlight 18"'),
        ('fundo preto para fotografia', 'Fundo preto para fotografia'),
        ('tv smart roku', 'TV Smart Roku'),
        ('seladora', 'Seladora'),
        ('ar condicionado', 'Ar condicionado'),
        ('wifi', 'WiFi'),
        ('água destilada', 'Água destilada'),
        ('alcool 70', 'Álcool 70'),
        ('papel interfolha', 'Papel interfolha'),
        ('plastificadora', 'Plastificadora')
    ]
    
    # Campo para tags personalizadas
    custom_tags = StringField('Outras Tags (separadas por vírgula)')
    
    submit = SubmitField('Salvar Sala')

# Formulário para configurar preços padrão
class DefaultPricesForm(FlaskForm):
    default_price_2h30 = FloatField('Preço Padrão 2h30', validators=[DataRequired()], default=90.0)
    default_price_1h15 = FloatField('Preço Padrão 1h15', validators=[DataRequired()], default=55.0)
    submit = SubmitField('Salvar Preços Padrão')

# Formulário para bloquear horário recorrente
class BlockedTimeForm(FlaskForm):
    day_of_week = SelectField('Dia da Semana', choices=[
        ('monday', 'Segunda-feira'), ('tuesday', 'Terça-feira'), ('wednesday', 'Quarta-feira'),
        ('thursday', 'Quinta-feira'), ('friday', 'Sexta-feira'), ('saturday', 'Sábado'),
        ('sunday', 'Domingo')
    ], validators=[DataRequired()])
    start_time = TimeField('Hora de Início', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('Hora de Fim', format='%H:%M', validators=[DataRequired()])
    submit = SubmitField('Bloquear Horário')

# Formulário para agendar aumento de preço
class PriceIncreaseForm(FlaskForm):
    new_price_2h30 = FloatField('Novo Preço 2h30', validators=[DataRequired()])
    new_price_1h15 = FloatField('Novo Preço 1h15', validators=[DataRequired()])
    scheduled_date = DateField('Data do Aumento', format='%Y-%m-%d', validators=[DataRequired()])
    notification_message = TextAreaField('Mensagem de Notificação', validators=[DataRequired()])
    submit = SubmitField('Programar Aumento')

# Formulário para equipamento/tag
class EquipmentForm(FlaskForm):
    name = StringField('Nome do Equipamento/Tag', validators=[DataRequired()])
    submit = SubmitField('Salvar')

# Formulário para equipamento alugável
class RentableEquipmentForm(FlaskForm):
    name = StringField('Nome do Equipamento para Aluguel', validators=[DataRequired()])
    description = TextAreaField('Descrição')
    daily_price = FloatField('Preço da Diária (R$)', validators=[DataRequired()])
    units_available = IntegerField('Unidades Disponíveis', validators=[DataRequired()])
    is_active = BooleanField('Ativo para Aluguel', default=True)
    submit = SubmitField('Salvar Equipamento')

# Formulário para tutorial
class TutorialForm(FlaskForm):
    title = StringField('Título do Tutorial', validators=[DataRequired()])
    video_url = StringField('URL do Vídeo (YouTube)', validators=[DataRequired(), URL()])
    description = TextAreaField('Descrição (Opcional)')
    submit = SubmitField('Salvar Tutorial')

# Formulário de configurações
class SettingsForm(FlaskForm):
    contract_text = TextAreaField('Texto do Contrato')
    login_video_url = StringField('URL do Vídeo de Login/Cadastro (YouTube)', validators=[DataRequired(), URL()])
    submit = SubmitField('Salvar Configurações')
