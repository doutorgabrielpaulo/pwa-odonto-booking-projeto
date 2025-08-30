import os
from app import create_app, db
from app.models.user import ParkingReservation, ParkingSpot, User
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA APLICAÇÃO ---
# Este script precisa carregar a aplicação Flask para ter acesso ao banco de dados
app = create_app()
app.app_context().push()

# --- FUNÇÃO PRINCIPAL DA TAREFA AGENDADA ---
def send_daily_garage_report():
    """
    Busca as reservas de garagem para o dia seguinte, formata o relatório
    e simula o envio para a empresa de estacionamento.
    Esta função será executada automaticamente todos os dias às 22h.
    """
    print("--- INICIANDO TAREFA AGENDADA: RELATÓRIO DA GARAGEM ---")
    
    # 1. Calcular a data de amanhã
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    # 2. Buscar todas as vagas de garagem ativas
    active_spots = ParkingSpot.query.filter_by(is_active=True).order_by(ParkingSpot.name).all()
    
    report_by_spot = {}
    
    # 3. Para cada vaga, buscar as reservas de amanhã
    for spot in active_spots:
        reservations = ParkingReservation.query.join(User).filter(
            ParkingReservation.spot_id == spot.id,
            ParkingReservation.reservation_date == tomorrow
        ).order_by(User.nome_completo).all() # Idealmente, ordenar por horário da reserva de sala
        
        if reservations:
            report_by_spot[spot.name] = []
            for res in reservations:
                user = res.user
                # Formata a linha para cada doutor
                # Futuramente, podemos adicionar o horário da reserva da sala aqui
                report_line = (
                    f"- 07h00-22h00 • {user.nome_completo} - "
                    f"modelo: {user.veiculo_modelo or 'Não informado'} | "
                    f"PLACA: {user.veiculo_placa or 'Não informada'}"
                )
                report_by_spot[spot.name].append(report_line)

    # 4. Montar o corpo do e-mail/mensagem
    if not report_by_spot:
        print(f"Nenhuma reserva de garagem encontrada para {tomorrow.strftime('%d/%m/%Y')}. Nenhuma ação necessária.")
        print("--- TAREFA FINALIZADA ---")
        return

    weekday_map = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    weekday = weekday_map[tomorrow.weekday()]
    
    subject = f"Olá, boa noite! 👋 Segue agenda de amanhã na unidade ATRIUM, {tomorrow.strftime('%d/%m/%Y')}, {weekday}:"
    
    message_body = [subject, ""] # Começa com o assunto e uma linha em branco

    for spot_name, lines in report_by_spot.items():
        message_body.append(f"✅ VAGA {spot_name}:")
        message_body.extend(lines)
        message_body.append("") # Linha em branco entre as vagas

    message_body.extend([
        "Obrigado! 🙏",
        "",
        "Atenciosamente, Dr. Gabriel"
    ])
    
    final_report = "\n".join(message_body)
    
    # 5. Simular o envio (no servidor real, isso enviaria o e-mail/whatsapp)
    print("\n--- RELATÓRIO GERADO ---")
    print(final_report)
    print("--- SIMULANDO ENVIO PARA CADASTRO@macpark.com.br e WhatsApp ---")
    print("--- TAREFA FINALIZADA ---\n")

# --- EXECUÇÃO DO SCRIPT ---
if __name__ == "__main__":
    send_daily_garage_report()
