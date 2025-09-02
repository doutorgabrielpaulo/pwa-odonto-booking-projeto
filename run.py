import os
from app import create_app, db
from app.models.user import User, Room, Reservation, SiteSettings, Tutorial, ApiLog, UserTutorialPreference, TempLock, ParkingSpot, ParkingReservation
from app.models.equipment import RentableEquipment, EquipmentReservation

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Room': Room, 
        'Reservation': Reservation,
        'SiteSettings': SiteSettings,
        'Tutorial': Tutorial,
        'ApiLog': ApiLog,
        'UserTutorialPreference': UserTutorialPreference,
        'TempLock': TempLock,
        'ParkingSpot': ParkingSpot,
        'ParkingReservation': ParkingReservation
    }

@app.cli.command('seed_db')
def seed_db_command():
    """Adiciona dados iniciais ao banco de dados."""
    import datetime

    # Seeding rooms
    db.session.query(Room).delete()
    
    room1 = Room(name='Cadeira Margarida', description='Sala 122 - 12° andar torre A', price_2h30=90.0, video_url='#', admin_notice='O refletor está com a luz um pouco fraca.')
    room2 = Room(name='Cadeira Tulipa', description='Sala 56 - 5° andar torre A', price_2h30=95.0, video_url='#')
    room3 = Room(name='Cadeira Lótus', description='Sala 56 - 5° andar torre A', price_2h30=95.0, video_url='#')
    
    db.session.add_all([room1, room2, room3])

    # Seeding site settings
    site_settings = SiteSettings(site_name='Odonto Booking', contact_email='contato@odontobooking.com')
    db.session.add(site_settings)

    # Seeding tutorials
    tutorial1 = Tutorial(title='Como usar a Cadeira Margarida', content='Instruções para ligar e operar a cadeira odontológica...', video_url='#')
    tutorial2 = Tutorial(title='Como esterilizar instrumentos', content='Passo a passo para usar a autoclave e a seladora...', video_url='#')
    db.session.add_all([tutorial1, tutorial2])

    # Seeding parking spots
    spot1 = ParkingSpot(name='Vaga 01', is_active=True)
    spot2 = ParkingSpot(name='Vaga 02', is_active=True)
    db.session.add_all([spot1, spot2])

    db.session.commit()
    print('Banco de dados populado com salas, configurações, tutoriais e vagas de garagem de exemplo!')
