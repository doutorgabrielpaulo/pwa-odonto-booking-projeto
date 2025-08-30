import os
from app import create_app, db
from app.models.user import User, Room, Equipment, Reservation # <-- LINHA ATUALIZADA

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Room': Room, 'Equipment': Equipment, 'Reservation': Reservation}

@app.cli.command('seed_db')
def seed_db_command():
    """Adiciona dados iniciais ao banco de dados."""
    import datetime

    db.session.query(Equipment).delete()
    db.session.query(Room).delete()
    
    equip1 = Equipment(name='Raio X')
    equip2 = Equipment(name='Fotopolimerizador')
    equip3 = Equipment(name='Bomba de Vácuo')
    equip4 = Equipment(name='Autoclave')
    db.session.add_all([equip1, equip2, equip3, equip4])
    
    room1 = Room(name='Cadeira Margarida', description='Sala 122 - 12° andar torre A', price_2h30=90.0, video_url='#', admin_notice='O refletor está com a luz um pouco fraca.')
    room2 = Room(name='Cadeira Tulipa', description='Sala 56 - 5° andar torre A', price_2h30=95.0, video_url='#')
    room3 = Room(name='Cadeira Lótus', description='Sala 56 - 5° andar torre A', price_2h30=95.0, video_url='#')
    
    room1.equipments.extend([equip2, equip4])
    room2.equipments.extend([equip1, equip2, equip3, equip4])
    room3.equipments.extend([equip1, equip2, equip3, equip4])
    
    db.session.add_all([room1, room2, room3])
    db.session.commit()
    print('Banco de dados populado com salas e equipamentos de exemplo!')
