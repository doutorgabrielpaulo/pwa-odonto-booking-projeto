# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import login_required, current_user, logout_user, login_user
from app.models.user import User, Room, Reservation, SiteSettings, Tutorial, ApiLog, UserTutorialPreference, TempLock, ParkingSpot, ParkingReservation, BlockedTime
from app.models.equipment import RentableEquipment, EquipmentReservation
from .. import db
from datetime import datetime, timedelta, date, time
from functools import wraps
from sqlalchemy import func
import os
import requests
import random
from markupsafe import Markup
from flask_mail import Message
import base64
import uuid
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename
from flask import current_app
from app.services.validation_service import log_event
import re
# Removemos a importação de get_youtube_id de utils pois vamos usar a função local
main = Blueprint('main', __name__)
# --- FUNÇÃO AUXILIAR PARA EXTRAIR ID DO YouTube ---
def get_youtube_id(url):
    if not url:
        return None
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None
# --- FUNÇÃO AUXILIAR PARA DETERMINAR NÍVEL E AVATAR ---
def get_user_level_and_avatar(user):
    score = user.score or 0
    gender = user.genero or 'masc' # Padrão para masculino se não definido
    
    # Lógica de Níveis
    if score < 50:
        level = 1
    elif score < 150:
        level = 2
    else:
        level = 3
        
    # Lógica do Avatar
    avatar_prefix = "avatar"
    if user.is_vip:
        avatar_prefix = "avatar_vip"
    else:
        avatar_prefix = f"avatar_level{level}"
        
    gender_suffix = "fem" if gender.lower() == 'feminino' else "masc"
    
    avatar_filename = f"{avatar_prefix}_{gender_suffix}.png"
    
    return level, avatar_filename
# --- DECORADOR DE VERIFICAÇÃO DE CONTRATO ---
def check_contract(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        current_contract_setting = SiteSettings.query.filter_by(key='contract_version').first()
        current_version = int(current_contract_setting.value) if current_contract_setting else 1
        if not current_user.is_admin and current_user.contract_accepted_version < current_version:
            return redirect(url_for('main.accept_contract'))
        return f(*args, **kwargs)
    return decorated_function
# --- FUNÇÃO AUXILIAR PARA GERAR SLOTS (MODIFICADA) ---
def generate_time_slots(date, all_unavailable):
    slots = { '2h30': [], '1h15': [] }
    base_slots_2h30 = [
        (time(7, 0), time(9, 30)), (time(9, 30), time(12, 0)),
        (time(12, 0), time(14, 30)), (time(14, 30), time(17, 0)),
        (time(17, 0), time(19, 30)), (time(19, 30), time(22, 0))
    ]
    base_slots_1h15 = [
        (time(7, 0), time(8, 15)), (time(8, 15), time(9, 30)),
        (time(9, 30), time(10, 45)), (time(10, 45), time(12, 0)),
        (time(12, 0), time(13, 15)), (time(13, 15), time(14, 30)),
        (time(14, 30), time(15, 45)), (time(15, 45), time(17, 0)),
        (time(17, 0), time(18, 15)), (time(18, 15), time(19, 30)),
        (time(19, 30), time(20, 45)), (time(20, 45), time(22, 0))
    ]
    
    def is_slot_occupied(start, end):
        for (res_start, res_end), slot_info in all_unavailable.items():
            # Verifica se há qualquer sobreposição
            if max(start, res_start) < min(end, res_end):
                return slot_info
        return None
        
    for start, end in base_slots_2h30:
        slot_info = is_slot_occupied(start, end)
        if slot_info:
            status = slot_info['status']
            user_name = slot_info.get('user_name', '')
        else:
            status = 'available'
            user_name = ''
            
        slots['2h30'].append({
            "start_str": start.strftime('%Hh%M'), "end_str": end.strftime('%Hh%M'),
            "start_for_form": start.isoformat(), "end_for_form": end.isoformat(),
            "status": status,
            "user_name": user_name
        })
        
    for start, end in base_slots_1h15:
        slot_info = is_slot_occupied(start, end)
        if slot_info:
            status = slot_info['status']
            user_name = slot_info.get('user_name', '')
        else:
            status = 'available'
            user_name = ''
            
        slots['1h15'].append({
            "start_str": start.strftime('%Hh%M'), "end_str": end.strftime('%Hh%M'),
            "start_for_form": start.isoformat(), "end_for_form": end.isoformat(),
            "status": status,
            "user_name": user_name
        })
        
    return slots
# --- ROTAS ---
@main.route('/dashboard')
@check_contract
def dashboard():
    # --- NOVA LÓGICA DE DADOS PARA O PAINEL ---
    level, avatar_filename = get_user_level_and_avatar(current_user)
    
    # Busca configurações do site
    show_fobs_setting = SiteSettings.query.filter_by(key='show_fobs').first()
    show_fobs = show_fobs_setting and show_fobs_setting.value == 'true'
    banner_setting = SiteSettings.query.filter_by(key='banner_gif_url').first()
    banner_url = banner_setting.value if banner_setting else url_for('static', filename='img/banner.gif')
    
    # Calcula métricas de desempenho
    reservas_pagas = Reservation.query.filter_by(user_id=current_user.id, is_paid=True).count()
    cancelamentos = ApiLog.query.filter_by(user_id=current_user.id, event_type='Cancelamento de Reserva').count()
    linha_media = reservas_pagas - cancelamentos
    
    # Busca e seleciona itens para o banner de destaques
    all_tutorials = Tutorial.query.all()
    if len(all_tutorials) > 3:
        highlight_items = random.sample(all_tutorials, 3)
    else:
        highlight_items = all_tutorials
        
    return render_template('dashboard.html', 
                            level=level, 
                            avatar_filename=avatar_filename,
                            show_fobs=show_fobs,
                            banner_url=banner_url,
                            reservas_pagas=reservas_pagas,
                            cancelamentos=cancelamentos,
                            linha_media=linha_media,
                            highlight_items=highlight_items)
@main.route('/alugar-sala', methods=['GET'])
@check_contract
def rent_room():
    # MODIFICADO: A rota agora passa as datas e a função get_youtube_id para o template
    selected_date_str = request.args.get('date', default=date.today().strftime('%Y-%m-%d'))
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    
    rooms = Room.query.filter_by(is_active=True, is_visible=True).order_by(Room.name).all()
    
    # ADICIONADO: Passando a função get_youtube_id para o template
    return render_template('rent_room.html', 
                           rooms=rooms, 
                           selected_date=selected_date, 
                           prev_date=prev_date, 
                           next_date=next_date,
                           get_youtube_id=get_youtube_id)  # <-- ESTA LINHA FOI ADICIONADA
@main.route('/get-room-info')
@check_contract
def get_room_info():
    room_id = request.args.get('room_id')
    
    if not room_id:
        return jsonify({'error': 'ID da sala não fornecido'}), 400
    
    try:
        room = Room.query.get_or_404(room_id)
        
        return jsonify({
            'id': room.id,
            'name': room.name,
            'description': room.description,
            'price_2h30': room.price_2h30,
            'price_1h15': room.price_1h15,
            'video_url': room.video_url,
            'video_tutorial_url': room.video_tutorial_url,
            'video_tutorial_autoclave_url': room.video_tutorial_autoclave_url,
            'video_tutorial_raiox_url': room.video_tutorial_raiox_url,
            'video_tutorial_plastificadora_url': room.video_tutorial_plastificadora_url,
            'admin_notice': room.admin_notice,
            'allow_1h15_rental': room.allow_1h15_rental,
            'is_visible': room.is_visible,
            'equipments': [{'id': e.id, 'name': e.name} for e in room.equipments]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@main.route('/book-room', methods=['POST'])
@check_contract
def book_room():
    data = request.json
    room_id = data.get('room_id')
    date_str = data.get('date')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
        
        # Verificar se já existe uma reserva para este horário
        existing_reservation = Reservation.query.filter_by(
            room_id=room_id,
            reservation_date=selected_date,
            start_time=start_time
        ).first()
        
        if existing_reservation:
            return jsonify({'success': False, 'message': 'O horário já está reservado.'}), 409
        
        # Verificar se há bloqueios temporários para este horário
        now = datetime.utcnow()
        existing_lock = TempLock.query.filter(
            TempLock.room_id == room_id,
            TempLock.date == selected_date,
            TempLock.start_time == start_time,
            TempLock.expires_at > now
        ).first()
        
        if existing_lock:
            return jsonify({'success': False, 'message': 'O horário está temporariamente bloqueado.'}), 409
        
        # Verificar se há horários bloqueados recorrentes
        day_of_week = selected_date.strftime('%A').lower()
        existing_blocked_time = BlockedTime.query.filter_by(
            room_id=room_id,
            day_of_week=day_of_week
        ).filter(
            (BlockedTime.start_time <= start_time) & (BlockedTime.end_time > start_time) |
            (BlockedTime.start_time < end_time) & (BlockedTime.end_time >= end_time) |
            (BlockedTime.start_time >= start_time) & (BlockedTime.end_time <= end_time)
        ).first()
        
        if existing_blocked_time:
            return jsonify({'success': False, 'message': 'Este horário está bloqueado.'}), 409
        
        # Criar a reserva
        new_reservation = Reservation(
            reservation_date=selected_date,
            start_time=start_time,
            end_time=end_time,
            user_id=current_user.id,
            room_id=room_id
        )
        
        # Calcular o preço total
        room = Room.query.get(room_id)
        duration = (datetime.combine(selected_date, end_time) - datetime.combine(selected_date, start_time)).total_seconds() / 3600
        
        if duration <= 1.25:  # 1h15
            new_reservation.total_price = room.price_1h15
        else:  # 2h30
            new_reservation.total_price = room.price_2h30
        
        db.session.add(new_reservation)
        db.session.commit()
        
        log_event("Reserva de Sala", "SUCCESS", 
                  {"room_id": room_id, "date": date_str, "start_time": start_time_str, "end_time": end_time_str}, 
                  user_id=current_user.id, ip_address=request.remote_addr)
        
        # Retorna sucesso para o JavaScript continuar o fluxo
        return jsonify({'success': True, 'message': 'Reserva criada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
@main.route('/check-tutorials', methods=['POST'])
@check_contract
def check_tutorials():
    data = request.json
    room_id = data.get('roomId')
    room = Room.query.get_or_404(room_id)
    # Verifica se o utilizador já dispensou os tutoriais para esta sala
    autoclave_pref = UserTutorialPreference.query.filter_by(user_id=current_user.id, room_id=room_id, tutorial_type='autoclave', dont_remind=True).first()
    plast_pref = UserTutorialPreference.query.filter_by(user_id=current_user.id, room_id=room_id, tutorial_type='plastificadora', dont_remind=True).first()
    questions = []
    if not autoclave_pref and room.video_tutorial_autoclave_url:
        questions.append({'id': 'autoclave', 'name': 'Autoclave', 'url': room.video_tutorial_autoclave_url})
    
    if not plast_pref and room.video_tutorial_plastificadora_url:
        questions.append({'id': 'plastificadora', 'name': 'Plastificadora', 'url': room.video_tutorial_plastificadora_url})
    return jsonify({'show_popup': len(questions) > 0, 'questions': questions})
@main.route('/save-tutorial-preference', methods=['POST'])
@check_contract
def save_tutorial_preference():
    data = request.json
    room_id = data.get('room_id')
    tutorial_type = data.get('tutorial_type')
    # Verifica se a preferência já existe para evitar duplicatas
    preference = UserTutorialPreference.query.filter_by(
        user_id=current_user.id,
        room_id=room_id,
        tutorial_type=tutorial_type
    ).first()
    if not preference:
        preference = UserTutorialPreference(
            user_id=current_user.id,
            room_id=room_id,
            tutorial_type=tutorial_type,
            dont_remind=True
        )
        db.session.add(preference)
    else:
        preference.dont_remind = True
    
    db.session.commit()
    log_event("Preferencia de Tutorial Salva", "SUCCESS", {"room_id": room_id, "tutorial": tutorial_type}, user_id=current_user.id, ip_address=request.remote_addr)
    return jsonify({'success': True})
@main.route('/gerar-mensagem-paciente', methods=['POST'])
@login_required
def gerar_mensagem_paciente():
    try:
        data = request.get_json()
        template_type = data.get('template_type')
        if not template_type:
            return jsonify({'error': 'Tipo de template não fornecido'}), 400
        prompts = {
            "lembrete": "um lembrete amigável de consulta. Inclua placeholders para [Nome do Paciente], [Data da Consulta] e [Hora da Consulta].",
            "pos_operatorio": "instruções de cuidados pós-operatórios para uma extração de dente simples.",
            "agradecimento": "uma mensagem de agradecimento a um novo paciente após a sua primeira consulta."
        }
        prompt_detail = prompts.get(template_type, "uma mensagem geral sobre saúde bucal.")
        system_prompt = "Aja como um assistente de consultório odontológico chamado OdontoBot. Seja profissional, amigável e conciso."
        user_query = f"Escreva uma mensagem para um paciente sobre: {prompt_detail}"
        api_key = os.environ.get("GEMINI_API_KEY") # Use uma variável de ambiente
        if not api_key:
            return jsonify({'error': 'Chave de API não configurada.'}), 500
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
        }
        response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()
        generated_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Não foi possível gerar a mensagem.')
        return jsonify({'message': generated_text})
    except requests.exceptions.RequestException as e:
        print(f"Erro na API do Gemini: {e}")
        return jsonify({'error': 'O serviço de IA está indisponível.'}), 503
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return jsonify({'error': 'Ocorreu um erro interno.'}), 500
@main.route('/mensagens-pacientes')
@check_contract
def patient_messages():
    return render_template('patient_messages.html')
@main.route('/deletar-conta', methods=['GET', 'POST'])
@check_contract
def delete_account():
    if request.method == 'POST':
        user = current_user
        # Lógica de "soft delete": desativa o usuário em vez de apagar
        user.is_active = False 
        db.session.commit()
        
        # (Opcional) Loga o evento no Templog
        # log_event(...)
        
        logout_user() # Faz o logout do usuário após desativar a conta
        flash('Sua conta foi desativada com sucesso.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('delete_account.html')  
@main.route('/alugar-equipamento', methods=['GET'])
@check_contract
def rent_equipment():
    selected_date_str = request.args.get('date', default=date.today().strftime('%Y-%m-%d'))
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    # Busca todos os equipamentos ativos
    equipments = RentableEquipment.query.filter_by(is_active=True).all()
    
    equipments_with_availability = []
    for equip in equipments:
        # Conta quantas reservas existem para este equipamento nesta data
        reserved_units = db.session.query(func.count(EquipmentReservation.id)).filter_by(
            equipment_id=equip.id, 
            reservation_date=selected_date
        ).scalar()
        
        available_units = equip.units_available - reserved_units
        
        equipments_with_availability.append({
            'equipment': equip,
            'available': available_units > 0,
            'available_count': available_units
        })
    return render_template('rent_equipment.html', 
                            equipments_data=equipments_with_availability,
                            selected_date=selected_date,
                            prev_date=prev_date,
                            next_date=next_date)
@main.route('/tutoriais')
@check_contract
def tutorials():
    tutorials = Tutorial.query.order_by(Tutorial.title).all()
    return render_template('tutorials.html', tutorials=tutorials)
@main.route('/book-equipment', methods=['POST'])
@check_contract
def book_equipment():
    equipment_id = request.form.get('equipment_id')
    date_str = request.form.get('date')
    equipment = RentableEquipment.query.get_or_404(equipment_id)
    
    # Lógica para criar a reserva do equipamento
    new_reservation = EquipmentReservation(
        reservation_date=date.fromisoformat(date_str),
        user_id=current_user.id,
        equipment_id=equipment_id,
        price=equipment.daily_price
    )
    db.session.add(new_reservation)
    db.session.commit()
    
    flash(f'{equipment.name} reservado com sucesso para {date.fromisoformat(date_str).strftime("%d/%m/%Y")}!', 'success')
    return redirect(url_for('main.my_reservations'))
    
@main.route('/minhas-reservas')
@check_contract
def my_reservations():
    today = date.today()
    # Query para reservas de sala
    upcoming_room_reservations = Reservation.query.filter(
        Reservation.user_id == current_user.id,
        Reservation.reservation_date >= today
    ).order_by(Reservation.reservation_date, Reservation.start_time).all()
    
    # Query para reservas de equipamento
    upcoming_equipment_reservations = EquipmentReservation.query.filter(
        EquipmentReservation.user_id == current_user.id,
        EquipmentReservation.reservation_date >= today
    ).order_by(EquipmentReservation.reservation_date).all()
    # Query para reservas de estacionamento
    upcoming_parking_reservations = ParkingReservation.query.filter(
        ParkingReservation.user_id == current_user.id,
        ParkingReservation.reservation_date >= today
    ).order_by(ParkingReservation.reservation_date).all()
    
    # Combina e ordena as reservas futuras
    upcoming_reservations = sorted(
        upcoming_room_reservations + upcoming_equipment_reservations + upcoming_parking_reservations,
        key=lambda r: r.reservation_date
    )
    # Lógica para reservas passadas (pode ser combinada similarmente se necessário)
    past_reservations = Reservation.query.filter(
        Reservation.user_id == current_user.id,
        Reservation.reservation_date < today
    ).order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc()).all()
    
    return render_template('my_reservations.html',
                            upcoming_reservations=upcoming_reservations,
                            past_reservations=past_reservations)
# --- ROTA DE OBTENÇÃO DE SLOTS (MODIFICADA) ---
@main.route('/get-room-slots')
@login_required
def get_room_slots():
    print("Rota /get-room-slots acessada")  # Log para diagnóstico
    room_id = request.args.get('room_id')
    date_str = request.args.get('date')
    
    print(f"Parâmetros recebidos: room_id={room_id}, date={date_str}")  # Log para diagnóstico
    
    if not room_id or not date_str:
        print("Parâmetros ausentes")  # Log para diagnóstico
        return jsonify({'error': 'Parâmetros ausentes'}), 400
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        room = Room.query.get_or_404(room_id)
        
        print(f"Sala encontrada: {room.name}")  # Log para diagnóstico
        
        # Verificar reservas existentes
        reservations_for_room = Reservation.query.filter_by(room_id=room.id, reservation_date=selected_date).all()
        print(f"Reservas encontradas: {len(reservations_for_room)}")  # Log para diagnóstico
        
        # Verificar bloqueios temporários ativos
        now = datetime.utcnow()
        temp_locks = TempLock.query.filter(
            TempLock.room_id == room.id,
            TempLock.date == selected_date,
            TempLock.expires_at > now
        ).all()
        print(f"Bloqueios temporários encontrados: {len(temp_locks)}")  # Log para diagnóstico
        
        # Verificar horários bloqueados
        blocked_times = BlockedTime.query.filter_by(room_id=room.id).all()
        print(f"Horários bloqueados encontrados: {len(blocked_times)}")  # Log para diagnóstico
        
        # Combinar reservas, bloqueios temporários e horários bloqueados
        reserved_times = {}
        for res in reservations_for_room:
            # Obter apenas o primeiro nome do usuário
            user_name = res.user.name.split()[0] if res.user.name else 'Usuário'
            reserved_times[(res.start_time, res.end_time)] = {
                'status': 'reserved',
                'user_name': user_name
            }
        
        locked_times = {}
        for lock in temp_locks:
            locked_times[(lock.start_time, lock.end_time)] = {
                'status': 'locked'
            }
        
        # Adicionar horários bloqueados recorrentes
        day_of_week = selected_date.strftime('%A').lower()
        for blocked in blocked_times:
            if blocked.day_of_week == day_of_week:
                reserved_times[(blocked.start_time, blocked.end_time)] = {
                    'status': 'blocked'
                }
        
        # Combinar todos os horários indisponíveis
        all_unavailable = {**reserved_times, **locked_times}
        
        time_slots = generate_time_slots(selected_date, all_unavailable)
        
        print(f"Slots gerados: {time_slots}")  # Log para diagnóstico
        
        return jsonify({
            'room_id': room_id,
            'date': date_str,
            'slots': time_slots
        })
    except Exception as e:
        print(f"Erro na rota /get-room-slots: {str(e)}")  # Log para diagnóstico
        return jsonify({'error': str(e)}), 500
        
# --- ROTA DE CRIAÇÃO DE BLOQUEIO TEMPORÁRIO (NOVA) ---
@main.route('/create-temp-lock', methods=['POST'])
@check_contract
def create_temp_lock():
    data = request.json
    room_id = data.get('room_id')
    date_str = data.get('date')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    
    if not all([room_id, date_str, start_time_str, end_time_str]):
        return jsonify({'error': 'Parâmetros ausentes'}), 400
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
        
        # Verificar se já existe um bloqueio ou reserva para este horário
        existing_reservation = Reservation.query.filter_by(
            room_id=room_id,
            reservation_date=selected_date,
            start_time=start_time
        ).first()
        
        existing_lock = TempLock.query.filter(
            TempLock.room_id == room_id,
            TempLock.date == selected_date,
            TempLock.start_time == start_time,
            TempLock.expires_at > datetime.utcnow()
        ).first()
        
        if existing_reservation or existing_lock:
            return jsonify({'success': False, 'message': 'Horário já está reservado ou bloqueado.'}), 409
        
        # Criar bloqueio temporário (5 minutos)
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        new_lock = TempLock(
            room_id=room_id,
            date=selected_date,
            start_time=start_time,
            end_time=end_time,
            user_id=current_user.id,
            expires_at=expires_at
        )
        db.session.add(new_lock)
        db.session.commit()
        
        return jsonify({'success': True, 'lock_id': new_lock.id, 'expires_at': expires_at.isoformat()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ROTA DE LIBERAÇÃO DE BLOQUEIO TEMPORÁRIO (NOVA) ---
@main.route('/release-temp-lock', methods=['POST'])
@check_contract
def release_temp_lock():
    data = request.json
    lock_id = data.get('lock_id')
    
    if not lock_id:
        return jsonify({'error': 'ID do bloqueio não fornecido'}), 400
    
    try:
        # Buscar e excluir o bloqueio temporário
        temp_lock = TempLock.query.get(lock_id)
        if temp_lock:
            db.session.delete(temp_lock)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Bloqueio não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ROTA DE RENT PARKING (NOVA) ---
@main.route('/alugar-estacionamento', methods=['GET'])
@check_contract
def rent_parking():
    selected_date_str = request.args.get('date', default=date.today().strftime('%Y-%m-%d'))
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    all_spots = ParkingSpot.query.filter_by(is_active=True).all()
    spots_with_availability = []
    
    reserved_spots_ids = {
        res.spot_id for res in ParkingReservation.query.filter_by(reservation_date=selected_date).all()
    }
    for spot in all_spots:
        is_available = spot.id not in reserved_spots_ids
        spots_with_availability.append({
            'spot': spot,
            'is_available': is_available
        })
    
    return render_template('rent_parking.html',
                            spots_data=spots_with_availability,
                            selected_date=selected_date,
                            prev_date=prev_date,
                            next_date=next_date)
                            
# --- ROTA DE BOOK PARKING (NOVA) ---
@main.route('/book-parking', methods=['POST'])
@check_contract
def book_parking():
    spot_id = request.form.get('spot_id')
    date_str = request.form.get('date')
    selected_date = date.fromisoformat(date_str)
    
    # Verificar se a vaga já está reservada para esta data
    existing_reservation = ParkingReservation.query.filter_by(
        spot_id=spot_id,
        reservation_date=selected_date
    ).first()
    
    if existing_reservation:
        flash('Esta vaga de estacionamento já está reservada para esta data.', 'danger')
        return redirect(url_for('main.rent_parking', date=date_str))
    new_reservation = ParkingReservation(
        reservation_date=selected_date,
        user_id=current_user.id,
        spot_id=spot_id
    )
    
    db.session.add(new_reservation)
    db.session.commit()
    
    flash('Vaga de estacionamento reservada com sucesso!', 'success')
    return redirect(url_for('main.my_reservations'))
@main.route('/contrato', methods=['GET', 'POST'])
@login_required
def accept_contract():
    # Lógica para verificar se o contrato já foi aceito
    current_contract_setting = SiteSettings.query.filter_by(key='contract_version').first()
    current_version = int(current_contract_setting.value) if current_contract_setting else 1
    if current_user.contract_accepted_version >= current_version:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        selfie_file = request.files.get('selfie')
        document_file = request.files.get('document')
        signature_data = request.form.get('signature')
        if not selfie_file or not document_file or not signature_data or 'data:image/png;base64,None' in signature_data:
            flash('Por favor, envie a selfie, o documento e a assinatura.', 'danger')
            return redirect(url_for('main.accept_contract'))
        user = current_user
        user.selfie_filename = save_picture(selfie_file, user.id, 'selfie')
        user.document_filename = save_picture(document_file, user.id, 'document')
        user.signature_filename = save_signature(signature_data, user.id)
        # Simulação da Análise de IA
        log_event("Análise de Documentos (IA)", "SUCCESS", 
                  {"message": "Simulação: Selfie e Documento correspondem."}, 
                  user_id=user.id, ip_address=request.remote_addr)
        user.contract_accepted_version = current_version
        db.session.commit()
        
        log_event("Aceite de Contrato", "SUCCESS", 
                  {"version": user.contract_accepted_version}, 
                  user_id=user.id, ip_address=request.remote_addr)
        flash('Contrato aceito com sucesso! Bem-vindo(a) à Odonto Booking.', 'success')
        return redirect(url_for('main.dashboard'))
        
    contract_setting = SiteSettings.query.filter_by(key='contract_text').first()
    contract_text = contract_setting.value if contract_setting else "Nenhum contrato definido pelo administrador."
    return render_template('contract.html', contract_text=contract_text)
# --- Funções auxiliares para salvar imagens ---
def save_picture(form_picture, user_id, prefix):
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = f"{prefix}_{user_id}_{random_hex}{f_ext}"
    picture_path = os.path.join(current_app.root_path, 'static/uploads', picture_fn)
    
    output_size = (800, 800)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn
def save_signature(signature_data_url, user_id):
    if 'data:image/png;base64,' not in signature_data_url:
        return None
    header, encoded = signature_data_url.split(",", 1)
    data = base64.b64decode(encoded)
    
    random_hex = uuid.uuid4().hex
    signature_fn = f"signature_{user_id}_{random_hex}.png"
    signature_path = os.path.join(current_app.root_path, 'static/uploads', signature_fn)
    
    with open(signature_path, "wb") as f:
        f.write(data)
        
    return signature_fn
# --- Rota de teste para verificar se o blueprint está funcionando ---
@main.route('/test-api')
def test_api():
    return jsonify({'message': 'API está funcionando corretamente!'})
