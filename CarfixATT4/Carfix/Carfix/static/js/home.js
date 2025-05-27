// Capturar o clique no botão de buscar endereço e redirecionar para o mapa
document.getElementById("buscarBtn").addEventListener("click", function() {
    const endereco = document.getElementById("endereco").value;
    if (endereco.trim() === "") {
        alert("Digite um endereço!");
        return;
    }
    window.location.href = `/mapa?endereco=${encodeURIComponent(endereco)}`;
});
