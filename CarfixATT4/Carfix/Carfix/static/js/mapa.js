const apiKey = '5b3ce3597851110001cf6248cce09e9ecce544f68d83737035e9c42e'; // Sua chave OpenRouteService
const stadiaApiKey = 'f36f8ff9-68e9-447d-831b-0a25112ad521';

let userLat = null;
let userLng = null;
let map = L.map('map').setView([-12.9714, -38.5014], 13); // Definindo vista inicial para Salvador
let rotaAtual = null;
let marcadorOrigem = null;
let marcadorDestino = null;

// Ícones personalizados
const iconUsuario = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/64/64113.png',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
});

const iconDestino = L.icon({
    iconUrl: 'https://cdn-icons-png.flaticon.com/512/484/484167.png',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
});

// Função para pegar parâmetro da URL
function getQueryParam(param) {
    const params = new URLSearchParams(window.location.search);
    return params.get(param);
}

// Adiciona camada base Stadia Maps (Alidade Smooth)
L.tileLayer(`https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png?api_key=${stadiaApiKey}`, {
    maxZoom: 20,
    attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap contributors</a>'
}).addTo(map);

// Inicializa tudo após o carregamento da página
document.addEventListener("DOMContentLoaded", () => {
    tentarUsarGeolocalizacao();

    const enderecoParam = getQueryParam('endereco');
    if (enderecoParam) {
        // A busca da rota será feita depois que userLat/Lng estiverem definidos
    }
});

// Tenta pegar localização atual do usuário
function tentarUsarGeolocalizacao() {
    if (!navigator.geolocation) {
        alert("Geolocalização não suportada no navegador. Definindo origem padrão para Salvador.");
        userLat = -12.9714; // Latitude de Salvador
        userLng = -38.5014; // Longitude de Salvador
        atualizarUserMarker("Origem padrão (geolocalização falhou)");
        const enderecoParam = getQueryParam('endereco');
        if (enderecoParam) {
            buscarRota(enderecoParam);
        }
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            userLat = pos.coords.latitude;
            userLng = pos.coords.longitude;
            atualizarUserMarker("Você está aqui");
            const enderecoParam = getQueryParam('endereco');
            if (enderecoParam) {
                buscarRota(enderecoParam);
            }
        },
        (err) => {
            console.warn("Sem acesso à geolocalização. Definindo origem padrão para Salvador.");
            userLat = -12.9714; // Latitude de Salvador
            userLng = -38.5014; // Longitude de Salvador
            atualizarUserMarker("Origem padrão (geolocalização negada)");
            const enderecoParam = getQueryParam('endereco');
            if (enderecoParam) {
                buscarRota(enderecoParam);
            }
        }
    );
}

// Atualiza marcador do usuário com ícone personalizado e torna draggable
function atualizarUserMarker(texto) {
    if (!marcadorOrigem) {
        marcadorOrigem = L.marker([userLat, userLng], { icon: iconUsuario, draggable: true }).addTo(map);
        marcadorOrigem.bindPopup(texto).openPopup();

        // Atualiza a rota quando o marcador for movido
        marcadorOrigem.on('dragend', async function(e) {
            const pos = e.target.getLatLng();
            userLat = pos.lat;
            userLng = pos.lng;
            marcadorOrigem.bindPopup("Origem movida").openPopup();

            const enderecoParam = getQueryParam('endereco');
            if (enderecoParam) {
                const destino = await geocodificar(enderecoParam);
                if (destino) {
                    desenharRota([userLng, userLat], destino, "Destino: Oficina");
                }
            } else {
                map.setView([userLat, userLng], 14);
            }
        });
    } else {
        marcadorOrigem.setLatLng([userLat, userLng]).bindPopup(texto).openPopup();
    }
    map.setView([userLat, userLng], 14); // Centraliza o mapa na origem do usuário
}

// Permite clicar no mapa para alterar a origem
map.on('click', function (e) {
    userLat = e.latlng.lat;
    userLng = e.latlng.lng;
    atualizarUserMarker("Origem definida clicando no mapa");

    const enderecoParam = getQueryParam('endereco');
    if (enderecoParam) {
        buscarRota(enderecoParam);
    }
});

// Função para geocodificar endereço para [lng, lat]
async function geocodificar(endereco) {
    let url = `https://api.openrouteservice.org/geocode/search?api_key=${apiKey}&text=${encodeURIComponent(endereco)}`;

    // Coordenadas aproximadas de um bounding box para Salvador (min_lon,min_lat,max_lon,max_lat)
    const salvadorBoundingBox = '-38.56,-13.02,-38.38,-12.91';
    url += `&boundary.rect=${salvadorBoundingBox}`;

    if (userLat !== null && userLng !== null) {
        url += `&focus.point.lat=${userLat}&focus.point.lon=${userLng}`;
    } else {
        url += `&focus.point.lat=-12.9714&focus.point.lon=-38.5014`; // Fallback para Salvador
    }

    url += `&boundary.country=BR`;

    try {
        const resp = await fetch(url);
        const data = await resp.json();
        if (data.features?.length > 0) {
            return data.features[0].geometry.coordinates; // [lng, lat]
        }
        console.warn("Geocodificação: Não encontrou resultados precisos dentro da área de Salvador para:", endereco);
        return null;
    } catch (e) {
        console.error("Erro na geocodificação:", e);
        return null;
    }
}

// Função para buscar rota, recebe endereço opcional (por parâmetro ou pelo input com id 'endereco')
async function buscarRota(enderecoParam = null) {
    let inputDestino = enderecoParam;

    if (!inputDestino) {
        const inputElement = document.getElementById("endereco");
        if (!inputElement) {
            return;
        }
        inputDestino = inputElement.value;
    }

    if (!inputDestino) {
        alert("Nenhum endereço de destino fornecido.");
        return;
    }

    if (userLat === null || userLng === null) {
        alert("Aguardando a definição da origem (geolocalização ou clique no mapa). Tente novamente.");
        return;
    }

    const destino = await geocodificar(inputDestino);
    if (!destino) {
        alert("Endereço de destino não encontrado ou fora da área de Salvador.");
        return;
    }

    desenharRota([userLng, userLat], destino, "Destino: Oficina");
}

// Desenha a rota no mapa entre origem e destino
async function desenharRota(origem, destino, popupText) {
    const url = 'https://api.openrouteservice.org/v2/directions/foot-walking/geojson';
    const body = { coordinates: [origem, destino] };

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': apiKey,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        const data = await resp.json();

        if (!data.features || data.features.length === 0) {
            alert("Rota não encontrada.");
            return;
        }

        const coords = data.features[0].geometry.coordinates;
        const latlngs = coords.map(c => [c[1], c[0]]);

        if (rotaAtual) map.removeLayer(rotaAtual);
        rotaAtual = L.polyline(latlngs, { color: 'blue', weight: 5 }).addTo(map);

        if (marcadorDestino) map.removeLayer(marcadorDestino);
        marcadorDestino = L.marker([destino[1], destino[0]], { icon: iconDestino }).addTo(map).bindPopup(popupText).openPopup();

        const group = L.featureGroup([marcadorOrigem, marcadorDestino, rotaAtual]);
        map.fitBounds(group.getBounds(), { padding: [50, 50] });

    } catch (e) {
        console.error("Erro ao desenhar rota:", e);
        alert("Erro ao traçar rota.");
    }
}