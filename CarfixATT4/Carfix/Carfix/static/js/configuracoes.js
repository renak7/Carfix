// FUNÇÃO GENÉRICA PARA CONFIRMAR ALTERAÇÕES (Manter)
function confirmarAlteracao(btnId, getValuesFn, validarFn, atualizarInterfaceFn) {
    const btn = document.getElementById(btnId);
    if (btn) {
        btn.addEventListener('click', async function() {
            const valores = getValuesFn();
            const valido = validarFn(valores);
            if (valido === true) {
                try {
                    const resposta = await enviarRequisicao(this.dataset.url, valores);
                    if (resposta.ok) {
                        const json = await resposta.json();
                        alert(json.mensagem || 'Alteração realizada com sucesso!');
                        if (atualizarInterfaceFn) {
                            atualizarInterfaceFn(json);
                        }
                    } else {
                        const json = await resposta.json();
                        alert(json.erro || 'Erro ao realizar alteração.');
                    }
                } catch (erro) {
                    console.error('Erro na requisição:', erro);
                    alert('Erro de rede ao tentar realizar a alteração.');
                }
            } else {
                alert(valido);
            }
        });
    }
}

async function enviarRequisicao(url, dados) {
    return await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados) 
    });
}

// ================== SENHA ==================
toggleForm('btnAlterarSenha', 'liFormSenha');
confirmarAlteracao(
    'btnConfirmarSenha',
    () => ({
        senhaAtual: document.getElementById('senhaAtual')?.value || '',
        novaSenha: document.getElementById('novaSenha')?.value || '',
        confirmaSenha: document.getElementById('confirmaSenha')?.value || ''
    }),
    ({ senhaAtual, novaSenha, confirmaSenha }) => {
        if (!senhaAtual || !novaSenha || !confirmaSenha) return 'Preencha todos os campos.';
        if (novaSenha !== confirmaSenha) return 'As senhas não coincidem.';
        if (senhaAtual === novaSenha) return 'A nova senha deve ser diferente da atual.';
        return true;
    },
    (dados) => {
        // Se precisar atualizar algo na interface após a alteração da senha
    },
    document.querySelector('#btnConfirmarSenha').dataset.url = '/alterar_senha'
);

// ========== EMAIL ==========
toggleForm('btnAlterarEmail', 'liFormEmail');
confirmarAlteracao(
    'btnConfirmarEmail',
    () => ({
        novoEmail: document.getElementById('novoEmail')?.value || '',
        confirmaEmail: document.getElementById('confirmaEmail')?.value || ''
    }),
    ({ novoEmail, confirmaEmail }) => {
        if (!novoEmail || !confirmaEmail) return 'Preencha ambos os campos.';
        if (novoEmail !== confirmaEmail) return 'Os e-mails não coincidem.';
        return true;
    },
    (dados) => {
        if (dados.email) {
            document.getElementById('perfilEmail').textContent = dados.email;
        }
    },
    document.querySelector('#btnConfirmarEmail').dataset.url = '/alterar_email'
);

//ENDERECO
toggleForm('btnAlterarEndereco', 'liFormEndereco');
confirmarAlteracao(
    'btnConfirmarEndereco',
    () => ({
        novoEndereco: document.getElementById('novoEndereco')?.value || ''
    }),
    ({ novoEndereco }) => {
        if (!novoEndereco) return 'Preencha o novo endereço.';
        return true;
    },
    (dados) => {
        if (dados.novoEndereco) {
            document.getElementById('perfilEndereco').textContent = dados.novoEndereco;
        }
    },
    '/alterar_endereco'
);

// ========== NÚMERO ==========
toggleForm('btnAlterarNumero', 'liFormNumero');
confirmarAlteracao(
    'btnConfirmarNumero',
    () => ({
        novoNumero: document.getElementById('novoNumero')?.value || ''
    }),
    ({ novoNumero }) => { // Alterado para usar o nome correto do campo
        if (!novoNumero) return 'Preencha o novo número.';
        if (!/^\+?\d{10,15}$/.test(novoNumero)) return 'Número inválido. Ex: +559955544000';
        return true;
    },
    (dados) => {
        if (dados.novoNumero) { // Alterado para usar o nome correto do campo
            document.getElementById('perfilNumero').textContent = dados.novoNumero;
        }
    },
    '/alterar_numero' // Removido document.querySelector().dataset.url, o URL já está aqui
);

// ========== USUÁRIO ==========
toggleForm('btnAlterarUsuario', 'liFormUsuario');
confirmarAlteracao(
    'btnConfirmarUsuario',
    () => ({
        nome: document.getElementById('novoUsuario')?.value || ''
    }),
    ({ nome }) => {
        if (!nome) return 'Preencha o novo nome de usuário.';
        if (nome.length < 3) return 'Nome de usuário deve ter ao menos 3 caracteres.';
        return true;
    },
    (dados) => {
        if (dados.nome) {
            document.getElementById('perfilNome').textContent = dados.nome;
        }
    },
    document.querySelector('#btnConfirmarUsuario').dataset.url = '/alterar_usuario'
);

function confirmarAlteracao(btnId, getValuesFn, validarFn, atualizarInterfaceFn, url) { // Adicionado parâmetro url
    const btn = document.getElementById(btnId);
    if (btn) {
        btn.addEventListener('click', async function() {
            const valores = getValuesFn();
            const valido = validarFn(valores);
            if (valido === true) {
                try {
                    const resposta = await enviarRequisicao(url, valores); // Usando o parâmetro url
                    if (resposta.ok) {
                        const json = await resposta.json();
                        alert(json.mensagem || 'Alteração realizada com sucesso!');
                        if (atualizarInterfaceFn) {
                            atualizarInterfaceFn(json);
                        }
                    } else {
                        const json = await resposta.json();
                        alert(json.erro || 'Erro ao realizar alteração.');
                    }
                } catch (erro) {
                    console.error('Erro na requisição:', erro);
                    alert('Erro de rede ao tentar realizar a alteração.');
                }
            } else {
                alert(valido);
            }
        });
    }
}

function toggleForm(botaoId, formId) {
    const botao = document.getElementById(botaoId);
    const form = document.getElementById(formId);

    if (botao && form) {
        botao.addEventListener('click', function(event) {
            event.preventDefault(); // impede o comportamento padrão do link
            form.style.display = (form.style.display === 'none' || form.style.display === '') ? 'block' : 'none';
        });
    }
}

async function enviarRequisicao(url, dados) {
    return await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }, // Garantindo que o Content-Type está definido como application/json
        body: JSON.stringify(dados)
    });
}