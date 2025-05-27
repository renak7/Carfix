document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const conversationsList = document.getElementById('conversations');
    const contactsSidebar = document.getElementById('contacts-sidebar');
    const contactsList = document.getElementById('contacts-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const closeContactsBtn = document.getElementById('close-contacts');
    const chatTitle = document.getElementById('chat-title');
    const contactSearch = document.getElementById('contact-search');

    let currentUser = null;
    let currentRoom = 'principal';

    const displayedMessages = new Set();

    function init() {
        fetchUserProfile();
        setupEventListeners();
        connectToSocket();
    }

    function fetchUserProfile() {
        fetch('/perfil_data')
            .then(response => {
                if (!response.ok) throw new Error('Erro ao buscar perfil');
                return response.json();
            })
            .then(data => {
                currentUser = data;
                loadConversations();
            })
            .catch(err => {
                console.error('Erro no perfil:', err);
                alert('Erro ao carregar perfil. Recarregue a página.');
            });
    }

    function setupEventListeners() {
        newChatBtn.addEventListener('click', showContacts);
        closeContactsBtn.addEventListener('click', hideContacts);
        messageForm.addEventListener('submit', handleMessageSubmit);
        contactSearch.addEventListener('input', handleContactSearch);

        messageInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                messageForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    function connectToSocket() {
        socket.on('connect', () => {
            console.log('Conectado ao Socket.IO');
            socket.emit('join_room', { room: currentRoom });
        });

        socket.on('disconnect', () => {
            console.log('Desconectado do Socket.IO');
        });

        socket.on('new_message', handleNewMessage);
        socket.on('new_private_message', handleNewMessage);

        socket.on('error', error => {
            console.error('Erro no socket:', error);
            alert('Erro na conexão com o chat. Recarregue a página.');
        });
    }

    function loadConversations() {
        fetch('/conversations')
            .then(res => {
                if (!res.ok) throw new Error('Erro ao carregar conversas');
                return res.json();
            })
            .then(convs => {
                renderConversations(convs);
                switchConversation('principal', 'Chat Geral');
            })
            .catch(err => {
                console.error(err);
                alert('Erro ao carregar conversas. Recarregue a página.');
            });
    }

    function renderConversations(conversations) {
        conversationsList.innerHTML = '';

        const generalChat = createConversationElement({
            uuid: 'principal',
            other_user: { nome: 'Chat Geral', img_perfil: '/static/imagens/icon2.png' },
            last_message: 'Conversa com todos os usuários'
        }, true);
        conversationsList.appendChild(generalChat);

        conversations.forEach(conv => {
            conversationsList.appendChild(createConversationElement(conv));
        });
    }

    function createConversationElement(conv, isGeneral = false) {
        const otherUser = {
            id: conv.other_user_id,
            nome: conv.other_user_nome || 'Chat Geral',
            img_perfil: conv.other_user_img || '/static/imagens/icon1.png'
        };

        const div = document.createElement('div');
        div.className = 'conversation' + (currentRoom === conv.uuid ? ' active' : '');
        div.setAttribute('data-room', conv.uuid);

        div.innerHTML = `
            <img src="${otherUser.img_perfil}" 
                 class="conversation-avatar"
                 alt="${otherUser.nome}">
            <div class="conversation-info">
                <div class="conversation-name">
                    ${otherUser.nome}
                    ${!isGeneral ? `<button class="visit-profile-btn" data-user-id="${otherUser.id}" title="Visitar perfil">👤</button>` : ''}
                </div>
                <div class="conversation-last-message">
                    ${conv.last_message || (isGeneral ? 'Conversa com todos os usuários' : 'Nenhuma mensagem')}
                </div>
            </div>
        `;

        div.addEventListener('click', () => {
            switchConversation(conv.uuid, otherUser.nome);
        });

        div.querySelector('.visit-profile-btn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            const userId = e.target.getAttribute('data-user-id');
            if (userId) {
                window.location.href = `/perfil/${userId}`;
            }
        });

        return div;
    }

    function switchConversation(room, title) {
        if (room === currentRoom) return;

        currentRoom = room;
        chatTitle.textContent = title;

        document.querySelectorAll('.conversation').forEach(conv => {
            conv.classList.toggle('active', conv.getAttribute('data-room') === room);
        });

        displayedMessages.clear();

        fetchChatHistory(room);
        socket.emit('join_room', { room: room });
    }

    function fetchChatHistory(room) {
        fetch(`/get_chat_history/${room}`)
            .then(res => {
                if (res.status === 401) {
                    window.location.href = '/';
                    return;
                }
                if (!res.ok) throw new Error('Erro ao carregar histórico');
                return res.json();
            })
            .then(messages => {
                chatMessages.innerHTML = '';
                messages.forEach(msg => {
                    if (!displayedMessages.has(msg.id)) {
                        addMessageToChat({
                            id: msg.id,
                            sender_id: msg.usuario_id,
                            sender_name: msg.sender_name,
                            message: msg.mensagem,
                            time: new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                            room: room
                        }, msg.usuario_id === currentUser.id);
                        displayedMessages.add(msg.id);
                    }
                });
                scrollToBottom();
            })
            .catch(err => {
                console.error(err);
                alert('Erro ao carregar histórico do chat.');
            });
    }

    function showContacts() {
        fetch('/contatos')
            .then(res => {
                if (!res.ok) throw new Error('Erro ao carregar contatos');
                return res.json();
            })
            .then(data => {
                renderContacts(data.contatos, data.sugestoes);
                contactsSidebar.style.display = 'flex';
            })
            .catch(err => {
                console.error(err);
                alert('Erro ao carregar contatos.');
            });
    }

    function hideContacts() {
        contactsSidebar.style.display = 'none';
    }

    function renderContacts(contacts, suggestions) {
        contactsList.innerHTML = '';

        if (contacts.length > 0) {
            const header = document.createElement('div');
            header.className = 'contacts-header';
            header.textContent = 'Seus contatos';
            contactsList.appendChild(header);
            contacts.forEach(contact => contactsList.appendChild(createContactElement(contact)));
        }

        if (suggestions.length > 0) {
            const header = document.createElement('div');
            header.className = 'contacts-header';
            header.textContent = 'Sugestões';
            contactsList.appendChild(header);
            suggestions.forEach(contact => contactsList.appendChild(createContactElement(contact, true)));
        }
    }

    function createContactElement(contact, isSuggested = false) {
        const div = document.createElement('div');
        div.className = 'contact-item';
        div.innerHTML = `
            <img src="${contact.img_perfil || '/static/uploads/user.png'}" 
                 class="contact-avatar"
                 alt="${contact.nome}">
            <div class="contact-info">
                <div class="contact-name">${contact.apelido || contact.nome}</div>
                <div class="contact-status">${isSuggested ? 'Adicionar como contato' : 'Contato'}</div>
            </div>
            ${isSuggested ? '<button class="contact-button">Adicionar</button>' : ''}
        `;

        div.addEventListener('click', () => {
            startPrivateChat(contact.id, contact.nome);
        });

        return div;
    }

    function handleContactSearch(e) {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.contact-item').forEach(item => {
            const name = item.querySelector('.contact-name').textContent.toLowerCase();
            item.style.display = name.includes(term) ? 'flex' : 'none';
        });
    }

    function startPrivateChat(userId, userName) {
        fetch(`/iniciar_chat_privado/${userId}`)
            .then(res => {
                if (!res.ok) throw new Error('Erro ao iniciar chat privado');
                return res.json();
            })
            .then(data => {
                switchConversation(data.sala_uuid, userName);
                loadConversations();
                hideContacts();
            })
            .catch(err => {
                console.error(err);
                alert('Erro ao iniciar conversa privada.');
            });
    }

    function handleMessageSubmit(e) {
        e.preventDefault();
        const message = messageInput.value.trim();

        if (!message) return;

        socket.emit('send_message', {
            room: currentRoom,
            message: message
        });

        messageInput.value = '';
    }

    function handleNewMessage(msg) {
        if (msg.room !== currentRoom) return;

        if (displayedMessages.has(msg.id)) return;

        addMessageToChat(msg, msg.sender_id === currentUser.id);
        displayedMessages.add(msg.id);
    }

    function addMessageToChat(msg, isSelf = false) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message' + (isSelf ? ' self' : '');

        messageElement.innerHTML = `
            <div class="message-sender">${isSelf ? 'Você' : msg.sender_name}</div>
            <div class="message-content">${msg.message}</div>
            <div class="message-time">${msg.time}</div>
        `;

        chatMessages.appendChild(messageElement);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    init();
});