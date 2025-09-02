from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models.user import User, Room, Reservation, SiteSettings, Tutorial, ApiLog, UserTutorialPreference, TempLock, ParkingSpot, ParkingReservation, BlockedTime
from app.models.equipment import RentableEquipment, EquipmentReservation, Equipment
from app.forms.forms import AdminEditUserForm, RoomForm, BlockedTimeForm, PriceIncreaseForm, EquipmentForm, RentableEquipmentForm, TutorialForm, SettingsForm, DefaultPricesForm
from app import db
import datetime
from functools import wraps
import re
from sqlalchemy import func
from contextlib import contextmanager

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

# --- Context Manager para evitar problemas de sessão ---
@contextmanager
def session_management():
    """Context manager para gerenciar sessões do SQLAlchemy e evitar avisos."""
    try:
        yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

# --- FUNÇÃO AUXILIAR PARA THUMBNAIL DO YOUTUBE (CORRIGIDA) ---
def get_youtube_thumbnail(url):
    """Extrai o ID de um vídeo do YouTube e retorna a URL da thumbnail."""
    if not url:
        return None
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    if match:
        video_id = match.group(1)
        return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    return None

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
    
@admin.route('/garage')
@admin_required
def garage_spots_list():
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
@admin.route('/manage_rooms')
@admin_required
def rooms_list():
    rooms = Room.query.order_by(Room.name).all()
    return render_template('admin_rooms_list.html', rooms=rooms)

@admin.route('/default-prices', methods=['GET', 'POST'])
@admin_required
def default_prices():
    form = DefaultPricesForm()
    
    # Buscar preços padrão atuais
    price_2h30_setting = SiteSettings.query.filter_by(key='default_price_2h30').first()
    price_1h15_setting = SiteSettings.query.filter_by(key='default_price_1h15').first()
    
    if form.validate_on_submit():
        # Salvar ou atualizar preços padrão
        if not price_2h30_setting:
            price_2h30_setting = SiteSettings(key='default_price_2h30')
            db.session.add(price_2h30_setting)
        price_2h30_setting.value = str(form.default_price_2h30.data)
        
        if not price_1h15_setting:
            price_1h15_setting = SiteSettings(key='default_price_1h15')
            db.session.add(price_1h15_setting)
        price_1h15_setting.value = str(form.default_price_1h15.data)
        
        db.session.commit()
        flash('Preços padrão atualizados com sucesso!', 'success')
        return redirect(url_for('admin.default_prices'))
    
    # Preencher formulário com valores atuais
    if price_2h30_setting:
        form.default_price_2h30.data = float(price_2h30_setting.value)
    if price_1h15_setting:
        form.default_price_1h15.data = float(price_1h15_setting.value)
    
    return render_template('admin_default_prices.html', form=form)

@admin.route('/room/new', methods=['GET', 'POST'])
@admin_required
def add_room():
    form = RoomForm()
    # Adicione este objeto de formulário para evitar o erro UndefinedError
    price_increase_form = PriceIncreaseForm()
    
    # Buscar preços padrão
    default_price_2h30 = 90.0
    default_price_1h15 = 55.0
    
    price_2h30_setting = SiteSettings.query.filter_by(key='default_price_2h30').first()
    price_1h15_setting = SiteSettings.query.filter_by(key='default_price_1h15').first()
    
    if price_2h30_setting:
        default_price_2h30 = float(price_2h30_setting.value)
    if price_1h15_setting:
        default_price_1h15 = float(price_1h15_setting.value)
    
    if form.validate_on_submit():
        with session_management():
            new_room = Room(
                name=form.name.data,
                description=form.description.data,
                price_2h30=form.price_2h30.data,
                price_1h15=form.price_1h15.data,
                video_url=form.video_url.data,
                video_tutorial_url=form.video_tutorial_url.data,
                video_tutorial_autoclave_url=form.video_tutorial_autoclave_url.data,
                video_tutorial_raiox_url=form.video_tutorial_raiox_url.data,
                video_tutorial_plastificadora_url=form.video_tutorial_plastificadora_url.data,
                admin_notice=form.admin_notice.data,
                allow_1h15_rental=form.allow_1h15_rental.data,
                is_visible=form.is_visible.data
            )
            
            db.session.add(new_room)
            db.session.flush()  # Garante que o objeto tenha um ID
            
            # Processar tags padrão (checkboxes)
            standard_tags = request.form.getlist('standard_tags')
            for tag_name in standard_tags:
                equipment = Equipment.query.filter(func.lower(Equipment.name) == func.lower(tag_name)).first()
                if not equipment:
                    equipment = Equipment(name=tag_name)
                    db.session.add(equipment)
                    db.session.flush()  # Garante que o equipment tenha um ID
                new_room.equipments.append(equipment)
            
            # Processar tags personalizadas (campo de texto)
            if form.custom_tags.data:
                custom_tags = [tag.strip() for tag in form.custom_tags.data.split(',') if tag.strip()]
                for tag_name in custom_tags:
                    # Verificar se já não foi adicionada como tag padrão
                    if tag_name.lower() not in [t.lower() for t in standard_tags]:
                        equipment = Equipment.query.filter(func.lower(Equipment.name) == func.lower(tag_name)).first()
                        if not equipment:
                            equipment = Equipment(name=tag_name)
                            db.session.add(equipment)
                            db.session.flush()  # Garante que o equipment tenha um ID
                        new_room.equipments.append(equipment)
            
            flash('Nova sala adicionada com sucesso!', 'success')
            return redirect(url_for('admin.rooms_list'))
    
    # Se for GET, preencher com preços padrão
    if request.method == 'GET':
        form.price_2h30.data = default_price_2h30
        form.price_1h15.data = default_price_1h15
    
    return render_template('admin_edit_room.html',
                           title="Adicionar Nova Sala",
                           form=form,
                           room=None,
                           price_increase_form=price_increase_form,
                           default_price_2h30=default_price_2h30,
                           default_price_1h15=default_price_1h15)

@admin.route('/room/<int:room_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    form = RoomForm(obj=room)
    
    # Buscar preços padrão
    default_price_2h30 = 90.0
    default_price_1h15 = 55.0
    
    price_2h30_setting = SiteSettings.query.filter_by(key='default_price_2h30').first()
    price_1h15_setting = SiteSettings.query.filter_by(key='default_price_1h15').first()
    
    if price_2h30_setting:
        default_price_2h30 = float(price_2h30_setting.value)
    if price_1h15_setting:
        default_price_1h15 = float(price_1h15_setting.value)
    
    if request.method == 'GET':
        # Preencher tags personalizadas (excluindo as padrão)
        standard_tag_values = [value for value, label in form.standard_tags]
        custom_tags = [e.name for e in room.equipments if e.name not in standard_tag_values]
        form.custom_tags.data = ', '.join(custom_tags)
        
        form.allow_1h15_rental.data = room.allow_1h15_rental
        form.is_visible.data = room.is_visible
        
    if form.validate_on_submit():
        with session_management():
            room.name = form.name.data
            room.description = form.description.data
            room.price_2h30 = form.price_2h30.data
            room.price_1h15 = form.price_1h15.data
            room.video_url = form.video_url.data
            room.video_tutorial_url = form.video_tutorial_url.data
            room.video_tutorial_autoclave_url = form.video_tutorial_autoclave_url.data
            room.video_tutorial_raiox_url = form.video_tutorial_raiox_url.data
            room.video_tutorial_plastificadora_url = form.video_tutorial_plastificadora_url.data
            room.admin_notice = form.admin_notice.data
            room.allow_1h15_rental = form.allow_1h15_rental.data
            room.is_visible = form.is_visible.data
            
            # Limpar todas as tags existentes
            room.equipments.clear()
            
            # Processar tags padrão (checkboxes)
            standard_tags = request.form.getlist('standard_tags')
            for tag_name in standard_tags:
                equipment = Equipment.query.filter(func.lower(Equipment.name) == func.lower(tag_name)).first()
                if not equipment:
                    equipment = Equipment(name=tag_name)
                    db.session.add(equipment)
                    db.session.flush()  # Garante que o equipment tenha um ID
                room.equipments.append(equipment)
            
            # Processar tags personalizadas (campo de texto)
            if form.custom_tags.data:
                custom_tags = [tag.strip() for tag in form.custom_tags.data.split(',') if tag.strip()]
                for tag_name in custom_tags:
                    # Verificar se já não foi adicionada como tag padrão
                    if tag_name.lower() not in [t.lower() for t in standard_tags]:
                        equipment = Equipment.query.filter(func.lower(Equipment.name) == func.lower(tag_name)).first()
                        if not equipment:
                            equipment = Equipment(name=tag_name)
                            db.session.add(equipment)
                            db.session.flush()  # Garante que o equipment tenha um ID
                        room.equipments.append(equipment)
            
            flash('Sala atualizada com sucesso!', 'success')
            return redirect(url_for('admin.rooms_list'))
    
    return render_template('admin_edit_room.html', 
                           form=form, 
                           title=f"Editando: {room.name}", 
                           room=room,
                           default_price_2h30=default_price_2h30,
                           default_price_1h15=default_price_1h15)
    
@admin.route('/room/<int:room_id>/delete', methods=['POST'])
@admin_required
def delete_room(room_id):
    with session_management():
        room = Room.query.get_or_404(room_id)
        db.session.delete(room)
        flash(f'Sala "{room.name}" deletada com sucesso!', 'success')
        return redirect(url_for('admin.rooms_list'))
    
@admin.route('/room/<int:room_id>/block-time', methods=['POST'])
@admin_required
def block_time(room_id):
    form = BlockedTimeForm()
    if form.validate_on_submit():
        with session_management():
            room = Room.query.get_or_404(room_id)
            existing_block = BlockedTime.query.filter_by(
                room_id=room.id,
                day_of_week=form.day_of_week.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data
            ).first()
            if existing_block:
                flash('Este bloqueio já existe para esta sala.', 'warning')
            else:
                new_blocked_time = BlockedTime(
                    room_id=room.id,
                    day_of_week=form.day_of_week.data,
                    start_time=form.start_time.data,
                    end_time=form.end_time.data
                )
                db.session.add(new_blocked_time)
                flash('Horário bloqueado com sucesso!', 'success')
    return redirect(url_for('admin.edit_room', room_id=room_id))

@admin.route('/settings/price-increase', methods=['POST'])
@admin_required
def price_increase():
    form = PriceIncreaseForm()
    if form.validate_on_submit():
        flash('Aumento de preço programado e notificação enviada!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo {field}: {error}", 'danger')
    
    return redirect(url_for('admin.site_settings'))

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
        with session_management():
            new_equipment = Equipment(name=form.name.data)
            db.session.add(new_equipment)
            flash('Equipamento/Tag adicionado com sucesso!', 'success')
    return redirect(url_for('admin.equipment_list'))

@admin.route('/equipment/<int:equipment_id>/delete', methods=['POST'])
@admin_required
def delete_equipment(equipment_id):
    with session_management():
        equipment = Equipment.query.get_or_404(equipment_id)
        db.session.delete(equipment)
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
        with session_management():
            new_equip = RentableEquipment(
                name=form.name.data, 
                description=form.description.data, 
                daily_price=form.daily_price.data, 
                units_available=form.units_available.data, 
                is_active=form.is_active.data
            )
            db.session.add(new_equip)
            flash('Equipamento para aluguel adicionado!', 'success')
            return redirect(url_for('admin.rentable_equipment_list'))
    return render_template('admin_edit_rentable_equipment.html', form=form, title="Adicionar Equipamento para Aluguel")

@admin.route('/rentable-equipment/<int:equipment_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_rentable_equipment(equipment_id):
    equip = RentableEquipment.query.get_or_404(equipment_id)
    form = RentableEquipmentForm(obj=equip)
    if form.validate_on_submit():
        with session_management():
            equip.name = form.name.data
            equip.description = form.description.data
            equip.daily_price = form.daily_price.data
            equip.units_available = form.units_available.data
            equip.is_active = form.is_active.data
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
        with session_management():
            new_tutorial = Tutorial(
                title=form.title.data, 
                video_url=form.video_url.data, 
                description=form.description.data
            )
            db.session.add(new_tutorial)
            flash('Tutorial adicionado com sucesso!', 'success')
    return redirect(url_for('admin.tutorials_list'))

@admin.route('/tutorials/<int:tutorial_id>/delete', methods=['POST'])
@admin_required
def delete_tutorial(tutorial_id):
    with session_management():
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        db.session.delete(tutorial)
        flash('Tutorial removido com sucesso!', 'success')
    return redirect(url_for('admin.tutorials_list'))

@admin.route('/settings', methods=['GET', 'POST'])
@admin_required
def site_settings():
    form = SettingsForm()
    contract = SiteSettings.query.filter_by(key='contract_text').first()
    video_url = SiteSettings.query.filter_by(key='login_video_url').first()
    if form.validate_on_submit():
        with session_management():
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
    with session_management():
        reservation = Reservation.query.get_or_404(reservation_id)
        if not reservation.is_paid:
            reservation.is_paid = True
            user = reservation.user
            user.score = (user.score or 0) + 8
            flash(f'Reserva de {user.nome_completo} marcada como paga. Score atualizado!', 'success')
        return redirect(url_for('admin.financial_panel'))
