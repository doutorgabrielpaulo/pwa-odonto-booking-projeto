# ARQUIVO: app/routes/admin.py (Completo e Atualizado)

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models.user import User, Reservation, Room, Equipment, RentableEquipment, Tutorial, SiteSettings
from app import db
import datetime
from functools import wraps
import re # NOVO: Import para extrair ID do YouTube
from sqlalchemy import func # NOVO: Import para usar func.lower()

# Importações para formulários
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional, URL
from wtforms_sqlalchemy.fields import QuerySelectMultipleField

admin = Blueprint('admin', __name__)

# --- Decorador Admin Required ---
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- FUNÇÃO AUXILIAR PARA THUMBNAIL DO YOUTUBE (NOVO) ---
def get_youtube_thumbnail(url):
    """Extrai o ID de um vídeo do YouTube e retorna a URL da thumbnail."""
    if not url:
        return None
    # Padrão para encontrar o ID em diferentes formatos de URL do YouTube
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    if match:
        video_id = match.group(1)
        return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    return None # Retorna None se não encontrar um ID válido

# --- Formulários ---
class AdminEditUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    score = IntegerField('Score')
    is_vip = BooleanField('Usuário VIP')
    is_chato = BooleanField('Usuário "Chato"')
    submit = SubmitField('Salvar Alterações')

def get_all_equipment():
    return Equipment.query.order_by(Equipment.name).all()

# --- ALTERAÇÃO AQUI: O formulário de salas agora usa um campo de texto para as tags ---
class RoomForm(FlaskForm):
    name = StringField('Nome da Cadeira/Sala', validators=[DataRequired()])
    description = StringField('Descrição (Ex: Sala 122 - 12° andar torre A)', validators=[DataRequired()])
    price_2h30 = FloatField('Preço 2h30', validators=[DataRequired()])
    price_1h15 = FloatField('Preço 1h15', validators=[DataRequired()])
    video_url = StringField('URL do Vídeo (YouTube)', validators=[Optional(), URL()])
    admin_notice = TextAreaField('Aviso do Admin (Opcional)')
    is_active = BooleanField('Sala Ativa', default=True)
    # Este campo substitui a lista de checkboxes
    equipments_tags = StringField('Equipamentos (Tags separadas por vírgula)')
    submit = SubmitField('Salvar Sala')

class EquipmentForm(FlaskForm):
    name = StringField('Nome do Equipamento/Tag', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class RentableEquipmentForm(FlaskForm):
    name = StringField('Nome do Equipamento para Aluguel', validators=[DataRequired()])
    description = TextAreaField('Descrição')
    daily_price = FloatField('Preço da Diária (R$)', validators=[DataRequired()])
    units_available = IntegerField('Unidades Disponíveis', validators=[DataRequired()])
    is_active = BooleanField('Ativo para Aluguel', default=True)
    submit = SubmitField('Salvar Equipamento')

class TutorialForm(FlaskForm):
    title = StringField('Título do Tutorial', validators=[DataRequired()])
    video_url = StringField('URL do Vídeo (YouTube)', validators=[DataRequired(), URL()])
    description = TextAreaField('Descrição (Opcional)')
    submit = SubmitField('Salvar Tutorial')

class SettingsForm(FlaskForm):
    contract_text = TextAreaField('Texto do Contrato')
    login_video_url = StringField('URL do Vídeo de Login/Cadastro (YouTube)', validators=[DataRequired(), URL()])
    submit = SubmitField('Salvar Configurações')

# --- Rotas Principais do Admin ---
@admin.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin_dashboard.html')

# --- Rotas de Gerenciamento de Usuários ---
@admin.route('/users')
@admin_required
def users_list():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.nome_completo).paginate(page=page, per_page=15)
    return render_template('admin_users_list.html', users=users)
    
    # --- ROTAS DE GERENCIAMENTO DE VAGAS (NOVAS) ---
@admin.route('/garage')
@admin_required
def garage_spots_list():
    # Esta página irá listar as vagas cadastradas (a ser construída)
    flash('Funcionalidade de gerenciamento de vagas em construção.', 'info')
    return redirect(url_for('admin.dashboard'))

@admin.route('/garage-report')
@admin_required
def garage_report_info():
    """Nova página que apenas informa sobre a automação."""
    return render_template('admin_garage_report.html')

@admin.route('/user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminEditUserForm(obj=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.nome_completo = form.nome_completo.data
        user.score = form.score.data
        user.is_vip = form.is_vip.data
        user.is_chato = form.is_chato.data
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.users_list'))
    return render_template('admin_edit_user.html', form=form, user=user)

# --- Rotas de Gerenciamento de Salas e Equipamentos ---
@admin.route('/rooms')
@admin_required
def rooms_list():
    # --- ALTERAÇÃO AQUI: Passa a URL da thumbnail para a página ---
    rooms = Room.query.order_by(Room.name).all()
    rooms_data = []
    for room in rooms:
        rooms_data.append({
            'room': room,
            'thumbnail': get_youtube_thumbnail(room.video_url)
        })
    return render_template('admin_rooms_list.html', rooms_data=rooms_data)

@admin.route('/room/new', methods=['GET', 'POST'])
@admin_required
def add_room():
    form = RoomForm()
    if form.validate_on_submit():
        new_room = Room(
            name=form.name.data, description=form.description.data,
            price_2h30=form.price_2h30.data, price_1h15=form.price_1h15.data,
            video_url=form.video_url.data, admin_notice=form.admin_notice.data,
            is_active=form.is_active.data
        )
        
        # --- ALTERAÇÃO AQUI: Lógica para processar as tags ---
        if form.equipments_tags.data:
            tags = [tag.strip() for tag in form.equipments_tags.data.split(',') if tag.strip()]
            for tag_name in tags:
                equipment = Equipment.query.filter(func.lower(Equipment.name) == func.lower(tag_name)).first()
                if not equipment:
                    equipment = Equipment(name=tag_name)
                    db.session.add(equipment)
                new_room.equipments.append(equipment)
        
        db.session.add(new_room)
        db.session.commit()
        flash('Nova sala adicionada com sucesso!', 'success')
        return redirect(url_for('admin.rooms_list'))
    return render_template('admin_edit_room.html', form=form, title="Adicionar Nova Sala")

@admin.route('/room/<int:room_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    form = RoomForm(obj=room)
    
    # --- ALTERAÇÃO AQUI: Lógica para pré-popular o campo de tags ---
    if request.method == 'GET':
        form.equipments_tags.data = ', '.join([e.name for e in room.equipments])

    if form.validate_on_submit():
        room.name = form.name.data; room.description = form.description.data
        room.price_2h30 = form.price_2h30.data; room.price_1h15 = form.price_1h15.data
        room.video_url = form.video_url.data; room.admin_notice = form.admin_notice.data
        room.is_active = form.is_active.data
        
        # --- ALTERAÇÃO AQUI: Lógica para atualizar as tags ---
        room.equipments.clear()
        if form.equipments_tags.data:
            tags = [tag.strip() for tag in form.equipments_tags.data.split(',') if tag.strip()]
            for tag_name in tags:
                equipment = Equipment.query.filter(func.lower(Equipment.name) == func.lower(tag_name)).first()
                if not equipment:
                    equipment = Equipment(name=tag_name)
                    db.session.add(equipment)
                room.equipments.append(equipment)

        db.session.commit()
        flash('Sala atualizada com sucesso!', 'success')
        return redirect(url_for('admin.rooms_list'))
    return render_template('admin_edit_room.html', form=form, title=f"Editando: {room.name}")
    
@admin.route('/equipment')
@admin_required
def equipment_list():
    equipments = Equipment.query.order_by(Equipment.name).all()
    form = EquipmentForm()
    return render_template('admin_equipment_list.html', equipments=equipments, form=form)

@admin.route('/equipment/add', methods=['POST'])
@admin_required
def add_equipment():
    form = EquipmentForm()
    if form.validate_on_submit():
        new_equipment = Equipment(name=form.name.data)
        db.session.add(new_equipment)
        db.session.commit()
        flash('Equipamento/Tag adicionado com sucesso!', 'success')
    return redirect(url_for('admin.equipment_list'))

@admin.route('/equipment/<int:equipment_id>/delete', methods=['POST'])
@admin_required
def delete_equipment(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    db.session.delete(equipment)
    db.session.commit()
    flash('Equipamento/Tag removido com sucesso!', 'success')
    return redirect(url_for('admin.equipment_list'))

@admin.route('/rentable-equipment')
@admin_required
def rentable_equipment_list():
    equipments = RentableEquipment.query.all()
    return render_template('admin_rentable_equipment_list.html', equipments=equipments)

@admin.route('/rentable-equipment/new', methods=['GET', 'POST'])
@admin_required
def add_rentable_equipment():
    form = RentableEquipmentForm()
    if form.validate_on_submit():
        new_equip = RentableEquipment(name=form.name.data, description=form.description.data, daily_price=form.daily_price.data, units_available=form.units_available.data, is_active=form.is_active.data)
        db.session.add(new_equip)
        db.session.commit()
        flash('Equipamento para aluguel adicionado!', 'success')
        return redirect(url_for('admin.rentable_equipment_list'))
    return render_template('admin_edit_rentable_equipment.html', form=form, title="Adicionar Equipamento para Aluguel")

@admin.route('/rentable-equipment/<int:equipment_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_rentable_equipment(equipment_id):
    equip = RentableEquipment.query.get_or_404(equipment_id)
    form = RentableEquipmentForm(obj=equip)
    if form.validate_on_submit():
        equip.name=form.name.data; equip.description=form.description.data; equip.daily_price=form.daily_price.data; equip.units_available=form.units_available.data; equip.is_active=form.is_active.data
        db.session.commit()
        flash('Equipamento para aluguel atualizado!', 'success')
        return redirect(url_for('admin.rentable_equipment_list'))
    return render_template('admin_edit_rentable_equipment.html', form=form, title=f"Editando: {equip.name}")

# --- Rotas de Tutoriais e Configurações ---
@admin.route('/tutorials')
@admin_required
def tutorials_list():
    tutorials = Tutorial.query.all()
    form = TutorialForm()
    return render_template('admin_tutorials.html', tutorials=tutorials, form=form)

@admin.route('/tutorials/add', methods=['POST'])
@admin_required
def add_tutorial():
    form = TutorialForm()
    if form.validate_on_submit():
        new_tutorial = Tutorial(title=form.title.data, video_url=form.video_url.data, description=form.description.data)
        db.session.add(new_tutorial)
        db.session.commit()
        flash('Tutorial adicionado com sucesso!', 'success')
    return redirect(url_for('admin.tutorials_list'))

@admin.route('/tutorials/<int:tutorial_id>/delete', methods=['POST'])
@admin_required
def delete_tutorial(tutorial_id):
    tutorial = Tutorial.query.get_or_404(tutorial_id)
    db.session.delete(tutorial)
    db.session.commit()
    flash('Tutorial removido com sucesso!', 'success')
    return redirect(url_for('admin.tutorials_list'))

@admin.route('/settings', methods=['GET', 'POST'])
@admin_required
def site_settings():
    form = SettingsForm()
    contract = SiteSettings.query.filter_by(key='contract_text').first()
    video_url = SiteSettings.query.filter_by(key='login_video_url').first()
    if form.validate_on_submit():
        if not contract:
            contract = SiteSettings(key='contract_text', value=form.contract_text.data)
            db.session.add(contract)
        else:
            contract.value = form.contract_text.data
        if not video_url:
            video_url = SiteSettings(key='login_video_url', value=form.login_video_url.data)
            db.session.add(video_url)
        else:
            video_url.value = form.login_video_url.data
        db.session.commit()
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('admin.site_settings'))
    if contract:
        form.contract_text.data = contract.value
    if video_url:
        form.login_video_url.data = video_url.value
    else:
        form.login_video_url.data = "https://www.youtube.com/embed/Z0u9_xUv0ms"
    return render_template('admin_settings.html', form=form)

# --- Rotas Financeiras e de Reservas ---
@admin.route('/reservas', methods=['GET', 'POST'])
@admin_required
def view_reservations():
    selected_date_str = request.form.get('selected_date', datetime.date.today().strftime('%Y-%m-%d'))
    selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    reservations = Reservation.query.filter_by(reservation_date=selected_date).order_by(Reservation.start_time).all()
    return render_template('admin_reservations.html', reservations=reservations, selected_date=selected_date)

@admin.route('/financial')
@admin_required
def financial_panel():
    unpaid_reservations = Reservation.query.filter_by(is_paid=False).order_by(Reservation.reservation_date).all()
    return render_template('admin_financials.html', unpaid=unpaid_reservations)

@admin.route('/mark-as-paid/<int:reservation_id>', methods=['POST'])
@admin_required
def mark_as_paid(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if not reservation.is_paid:
        reservation.is_paid = True
        user = reservation.user
        user.score = (user.score or 0) + 8
        db.session.commit()
        flash(f'Reserva de {user.nome_completo} marcada como paga. Score atualizado!', 'success')
    return redirect(url_for('admin.financial_panel'))
