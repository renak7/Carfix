// Pega o ID do usuário do input hidden
const usuarioId = document.getElementById('usuario-id')?.value;
const estrelas = document.querySelectorAll('.star');
const notaSpan = document.getElementById('nota');

let notaAtual = 0;

// Atualiza nome do arquivo selecionado no input file
document.getElementById('fileInput')?.addEventListener('change', function () {
  const nomeArquivo = this.files[0]?.name || 'Nenhum arquivo selecionado';
  document.getElementById('nome-arquivo').textContent = nomeArquivo;
});

// Efeito hover nas estrelas
estrelas.forEach((estrela, index) => {
  estrela.addEventListener('mouseover', () => {
    resetarEstrelas();
    for (let i = 0; i <= index; i++) {
      estrelas[i].classList.add('hover');
    }
  });

  estrela.addEventListener('mouseout', () => {
    resetarEstrelas();
    destacarNota(notaAtual);
  });

  estrela.addEventListener('click', () => {
    notaAtual = index + 1;
    notaSpan.textContent = notaAtual;
    destacarNota(notaAtual);
    enviarAvaliacao(notaAtual);
  });
});

function resetarEstrelas() {
  estrelas.forEach(e => {
    e.classList.remove('hover', 'selecionada');
  });
}

function destacarNota(nota) {
  for (let i = 0; i < nota; i++) {
    estrelas[i].classList.add('selecionada');
  }
}

function enviarAvaliacao(nota) {
  if (!usuarioId) {
    console.error('ID do usuário não definido.');
    return;
  }

  fetch("/avaliar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      usuarioId: usuarioId,
      nota: nota
    })
  })
    .then(response => response.json())
    .then(data => {
        if (data.mensagem) {
            alert(data.mensagem);
            location.reload();
  }     else if (data.error) {
            alert(`Erro: ${data.error}`);  // corrigido com crase e interpolação
  }
})

    .catch(error => {
      console.error("Erro ao enviar avaliação:", error);
    });
}

function atualizarMedia() {
  if (!usuarioId) {
    console.warn("Usuário ID não encontrado.");
    return;
  }

  fetch(`/media/${usuarioId}`)  // <-- crases para template string
    .then(response => {
      if (!response.ok) 
        throw new Error(`Resposta inválida do servidor: ${response.status}`); // crases
      return response.json();
    })
    .then(data => {
      document.getElementById('media-nota').textContent = data.media;
    })
    .catch(error => console.error('Erro ao buscar média:', error));
}

document.addEventListener('DOMContentLoaded', atualizarMedia);