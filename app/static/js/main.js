// ARQUIVO: app/static/js/main.js (Completo)
document.addEventListener('DOMContentLoaded', function() {
    
    // Máscara de telefone
    const whatsappInput = document.getElementById('whatsapp-input');
    if (whatsappInput) {
        whatsappInput.addEventListener('input', formatPhone);
    }
    
    // --- LÓGICA DO FORMULÁRIO DE CADASTRO ---
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        const passwordInput = document.getElementById('password');
        const password2Input = document.getElementById('password2');
        const passwordMatchError = document.getElementById('password-match-error');
        
        // Verificação de senhas em tempo real
        function checkPasswords() {
            if (passwordInput.value !== password2Input.value && password2Input.value.length > 0) {
                passwordMatchError.classList.remove('hidden');
            } else {
                passwordMatchError.classList.add('hidden');
            }
        }
        if (passwordInput && password2Input) {
            passwordInput.addEventListener('input', checkPasswords);
            password2Input.addEventListener('input', checkPasswords);
        }

        // Validação no clique do botão "Enviar"
        registerForm.addEventListener('submit', function(event) {
            event.preventDefault(); // Impede o envio imediato do formulário
            
            let errors = [];
            const fields = registerForm.elements;

            // Mapeia os nomes dos campos para mensagens amigáveis
            const fieldNames = {
                'nome_completo': 'Nome Completo', 'cro': 'Número do CRO', 'cpf': 'CPF',
                'whatsapp': 'WhatsApp', 'data_nascimento': 'Data de Nascimento',
                'email': 'E-mail', 'password': 'Senha', 'password2': 'Confirmação de Senha'
            };

            // Verifica campos de texto
            for (const fieldName in fieldNames) {
                if (fields[fieldName] && fields[fieldName].value.trim() === '') {
                    errors.push(`O campo "${fieldNames[fieldName]}" é obrigatório.`);
                }
            }

            // Verifica se as senhas conferem
            if (fields['password'].value !== fields['password2'].value) {
                errors.push('As senhas não conferem.');
            }

            // Verifica o aceite dos termos
            if (!fields['accept_terms'].checked) {
                errors.push('Você precisa aceitar os termos de uso.');
            }

            // Se houver erros, mostra o pop-up
            if (errors.length > 0) {
                const errorList = document.getElementById('error-list');
                const errorModal = document.getElementById('error-modal');
                
                errorList.innerHTML = ''; // Limpa a lista de erros anterior
                errors.forEach(error => {
                    const li = document.createElement('li');
                    li.textContent = error;
                    errorList.appendChild(li);
                });
                errorModal.classList.remove('hidden');
            } else {
                // Se não houver erros, envia o formulário
                HTMLFormElement.prototype.submit.call(registerForm);
            }
        });

        // Lógica para fechar o pop-up
        const closeModalBtn = document.getElementById('close-modal-btn');
        const errorModal = document.getElementById('error-modal');
        if (closeModalBtn && errorModal) {
            closeModalBtn.addEventListener('click', () => {
                errorModal.classList.add('hidden');
            });
        }
    }
});

function formatPhone(e) {
    let value = e.target.value.replace(/\D/g, '');
    let formattedValue = '';
    if (value.length > 0) { formattedValue = '(' + value.substring(0, 2); }
    if (value.length > 2) { formattedValue += ') ' + value.substring(2, 7); }
    if (value.length > 7) { formattedValue += '-' + value.substring(7, 11); }
    e.target.value = formattedValue;
}

// ##################################################################
// ### INÍCIO DA SEÇÃO ATUALIZADA ###
// ##################################################################

// --- LÓGICA DO TOGGLE DE HORÁRIOS PARA MÚLTIPLAS SALAS ---
const allToggles = document.querySelectorAll('.toggle-horarios');

allToggles.forEach(toggle => {
    toggle.addEventListener('change', function() {
        // Extrai o ID da sala a partir do ID do botão (ex: 'toggle-horarios-1' -> '1')
        const roomId = this.id.split('-').pop();
        
        // Seleciona os contêineres de horários específicos para essa sala
        const slots2h30 = document.getElementById(`slots-2h30-${roomId}`);
        const slots1h15 = document.getElementById(`slots-1h15-${roomId}`);

        if (slots2h30 && slots1h15) {
            if (this.checked) {
                // Mostra 1h15, esconde 2h30
                slots2h30.classList.add('hidden');
                slots1h15.classList.remove('hidden');
            } else {
                // Mostra 2h30, esconde 1h15
                slots2h30.classList.remove('hidden');
                slots1h15.classList.add('hidden');
            }
        }
    });
});

// ##################################################################
// ### FIM DA SEÇÃO ATUALIZADA ###
// ##################################################################
