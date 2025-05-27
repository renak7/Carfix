document.addEventListener('DOMContentLoaded', function () {
    const chatInput = document.querySelector(".chat-input textarea");
    const sendChatBtn = document.querySelector("#send-btn");
    const chatbox = document.querySelector(".chatbox");
    const chatbotToggler = document.querySelector(".chatbot-toggler");
    const chatbotCloseBtn = document.querySelector(".close-btn");
    const inputInitHeight = chatInput.scrollHeight;

    const responses = {
        "olá": "Oi! Como posso te ajudar hoje?\n\nDigite o número da opção desejada:\n1-Como redefinir a senha.\n2-Como alterar o email.\n3-Como alterar a foto de perfil.\n4-Como alterar o nome de usuário.\n5-Como alterar o número.",
        "oi": "Olá! Em que posso ajudar?\n\nDigite o número da opção desejada:\n1-Como redefinir a senha.\n2-Como alterar o email.\n3-Como alterar a foto de perfil.\n4-Como alterar o nome de usuário.\n5-Como alterar o número.",
        "1": "Configurações > Configurações e privacidade > Alterar senha > Digitar senha nova, digitar senha atual e confirmar a senha atual.\nSe tiver mais alguma dúvida, digite 0.",
        "2": "Configurações > Alterar email > Digite o email novo.\nSe tiver mais alguma dúvida, digite 0.",
        "3": "Perfil > Alterar imagem de perfil > Escolher arquivo > enviar.\nSe tiver mais alguma dúvida, digite 0.",
        "4": "Configurações > Atualizações cadastrais > Mudar nome de usuário > Inserir nome de usuário.\nSe tiver mais alguma dúvida, digite 0.",
        "5": "Configurações > Atualizações cadastrais > Mudar número > Inserir novo número.\nSe tiver mais alguma dúvida, digite 0.",
        "0": "Digite o número da opção desejada:\n1-Como redefinir a senha.\n2-Como alterar o email.\n3-Como alterar a foto de perfil.\n4-Como alterar o nome de usuário.\n5-Como alterar o número."
    };

    const createChatLi = (message, className) => {
        const chatLi = document.createElement("li");
        chatLi.classList.add("chat", className);
        chatLi.innerHTML = className === "outgoing"
            ? `<p>${message}</p>`
            : `<span class="material-symbols-outlined">smart_toy</span><p>${message}</p>`;
        return chatLi;
    };

    const saveChatHistory = () => {
        localStorage.setItem("chatHistory", chatbox.innerHTML);
    };

    const loadChatHistory = () => {
        const savedHistory = localStorage.getItem("chatHistory");
        if (savedHistory) {
            chatbox.innerHTML = savedHistory;
        }
    };

    const handleChat = () => {
        const userMessage = chatInput.value.trim().toLowerCase();
        if (!userMessage) return;

        chatInput.value = "";
        chatInput.style.height = `${inputInitHeight}px`;

        chatbox.appendChild(createChatLi(userMessage, "outgoing"));
        chatbox.scrollTo(0, chatbox.scrollHeight);
        saveChatHistory();

        setTimeout(() => {
            const response = responses[userMessage] || "Desculpe, não entendi. Pode reformular?";
            const incomingChatLi = createChatLi(response, "incoming");
            chatbox.appendChild(incomingChatLi);
            chatbox.scrollTo(0, chatbox.scrollHeight);
            saveChatHistory();
        }, 600);
    };

    chatInput.addEventListener("input", () => {
        chatInput.style.height = `${inputInitHeight}px`;
        chatInput.style.height = `${chatInput.scrollHeight}px`;
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleChat();
        }
    });

    sendChatBtn.addEventListener("click", handleChat);

    chatbotCloseBtn.addEventListener("click", () => {
        document.body.classList.remove("show-chatbot");
        chatbotToggler.setAttribute("aria-expanded", "false");
    });

    chatbotToggler.addEventListener("click", () => {
        document.body.classList.toggle("show-chatbot");
        const isExpanded = document.body.classList.contains("show-chatbot");
        chatbotToggler.setAttribute("aria-expanded", isExpanded.toString());
    });

    // carregar histórico salvo ao abrir a página
    loadChatHistory();
});