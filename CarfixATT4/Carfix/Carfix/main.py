from flask import Flask, render_template, request, flash, redirect, session, g, url_for, jsonify
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from flask_socketio import SocketIO, emit, join_room
import phonenumbers
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from datetime import datetime
import uuid
from flask import send_from_directory
import traceback
import requests

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'joaopedro'
app.config['DATABASE'] = 'usuarios.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

socketio = SocketIO(app, cors_allowed_origins="*")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Banco de dados
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db:
        db.close()

def create_table():
    db = get_db()

    db.execute('''
        CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tema TEXT DEFAULT '#3b5998',
            img_perfil TEXT DEFAULT '/static/imagens/icon2.png',
            img_capa TEXT DEFAULT '/static/imagens/fundo.jpg',
            email TEXT NOT NULL UNIQUE,
            celular TEXT UNIQUE,
            endereco TEXT,
            tipo TEXT CHECK(tipo IN ('cliente', 'mecanico')),
            cnpj TEXT
        );
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            mensagem TEXT NOT NULL,
            sala TEXT NOT NULL DEFAULT 'principal',
            sala_uuid TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuario (id)
        );
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS contatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            contato_id INTEGER NOT NULL,
            apelido TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuario (id),
            FOREIGN KEY (contato_id) REFERENCES usuario (id),
            UNIQUE(usuario_id, contato_id)
        );
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS salas_privadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT NOT NULL UNIQUE,
            usuario1_id INTEGER NOT NULL,
            usuario2_id INTEGER NOT NULL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario1_id) REFERENCES usuario (id),
            FOREIGN KEY (usuario2_id) REFERENCES usuario (id),
            UNIQUE(usuario1_id, usuario2_id)
        );
    ''')

    # Verifica e adiciona coluna sala_uuid se não existir
    try:
        db.execute("SELECT sala_uuid FROM mensagens LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE mensagens ADD COLUMN sala_uuid TEXT")
        db.commit()

def get_conversations(user_id):
    db = get_db()
    query = '''
    SELECT
        sp.uuid,
        u.id AS other_user_id,
        u.nome,
        u.img_perfil,
        (SELECT mensagem FROM mensagens m WHERE m.sala_uuid = sp.uuid ORDER BY timestamp DESC LIMIT 1) AS last_message
    FROM salas_privadas sp
    JOIN usuario u ON (CASE WHEN sp.usuario1_id = ? THEN sp.usuario2_id ELSE sp.usuario1_id END) = u.id
    WHERE sp.usuario1_id = ? OR sp.usuario2_id = ?
    '''

    rows = db.execute(query, (user_id, user_id, user_id)).fetchall()

    conversations = []
    for row in rows:
        # img_perfil pode ser None ou vazio? Se sim, garantir fallback no backend
        img_perfil = row['img_perfil']
        if not img_perfil:
            img_perfil = '/static/uploads/'  # arquivo padrão genérico

        conversations.append({
            'uuid': row['uuid'],
            'other_user': {
                'id': row['other_user_id'],
                'nome': row['nome'] or 'Usuário desconhecido',
                'img_perfil': img_perfil
            },
            'last_message': row['last_message'] or ''
        })

    return conversations

def conectar_db():
    return sqlite3.connect('avaliacoes.db')

def create_avaliacoes_table():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            avaliador_id INTEGER NOT NULL,
            nota INTEGER NOT NULL CHECK(nota BETWEEN 0 AND 5),
            FOREIGN KEY (usuario_id) REFERENCES usuario (id),
            FOREIGN KEY (avaliador_id) REFERENCES usuario (id),
            UNIQUE(avaliador_id, usuario_id)
        )
    ''')
    db.commit()

# Configuração inicial do banco de dados
with app.app_context():
    create_table()
    create_avaliacoes_table()

# Funções auxiliares
def celular_valido(numero, pais='BR'):
    try:
        parsed = phonenumbers.parse(numero, pais)
        return phonenumbers.is_valid_number(parsed) and phonenumbers.number_type(parsed) == phonenumbers.PhoneNumberType.MOBILE
    except:
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def enviar_email_verificacao(destinatario, codigo):
    remetente = "carfixofc@gmail.com"
    senha = "bpwojquxgsqhgkng" 
    assunto = "NÃO RESPONDA Código de Verificação"
    corpo = f"Seu código de verificação para a criação da sua conta é: {codigo}"

    msg = MIMEMultipart()
    msg["From"] = remetente
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
            servidor.starttls()
            servidor.login(remetente, senha)
            servidor.send_message(msg)
        print(f"E-mail enviado com sucesso para {destinatario}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

# Rotas principais
@app.route("/")
def login():
    return render_template('login.html')

@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")

@app.route("/acesso", methods=['POST'])
def acesso():
    nome = request.form.get('email')
    senha = request.form.get('senha')

    db = get_db()
    usuario = db.execute('SELECT * FROM usuario WHERE nome = ? OR email = ?', (nome, nome)).fetchone()

    if usuario and check_password_hash(usuario['senha'], senha):
        session['id'] = usuario['id']
        return redirect('/home')
    else:
        flash('Nome de usuário ou senha incorretos, tente novamente!!')
        return redirect('/')

@app.route("/cadastrando", methods=['POST'])
def cadastrando():
    nome = request.form.get('nome')
    senha = request.form.get('senha')
    email = request.form.get('email')
    celular = request.form.get('celular')
    tipo = request.form.get('escolha')
    cnpj = request.form.get('cnpj', '').strip().replace('.', '').replace('/', '').replace('-', '') if tipo == 'mecanico' else None

    tema = '#3b5998'
    img_capa = '/static/imagens/Fundo.png'
    img_perfil = '/static/imagens/user.png'

    if not celular or not celular_valido(celular):
        flash('Número de celular inválido ou não fornecido. Use o formato com DDD, ex: (11) 91234-5678.')
        return redirect('/cadastro')

    try:
        parsed = phonenumbers.parse(celular, 'BR')
        celular_formatado = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.phonenumberutil.NumberParseException as e:
        flash(f'Erro ao formatar número de celular: {str(e)}')
        return redirect('/cadastro')

    db = get_db()
    if db:
        try:
            cursor = db.cursor()
            cursor.execute('SELECT * FROM usuario WHERE email = ? OR celular = ? OR nome = ?', 
                           (email, celular_formatado, nome))
            existente = cursor.fetchone()
            if existente:
                if existente['email'] == email:
                    flash('Este e-mail já está em uso.')
                elif existente['celular'] == celular_formatado:
                    flash('Este número de celular já está em uso.')
                elif existente['nome'] == nome:
                    flash('Este nome de usuário já está em uso.')
                return redirect('/cadastro')
        except Exception as e:
            flash(f"Erro ao verificar usuário existente no banco de dados: {str(e)}")
            return redirect('/cadastro')

    endereco = None

    if tipo == 'mecanico':
        if not cnpj or len(cnpj) != 14:
            flash('Informe um CNPJ válido (14 dígitos).')
            return redirect('/cadastro')

        try:
            response = requests.get(f'https://brasilapi.com.br/api/cnpj/v1/{cnpj}', timeout=5)

            if response.status_code == 404:
                flash(f'CNPJ {cnpj} não encontrado na BrasilAPI.')
                return redirect('/cadastro')
            elif response.status_code != 200:
                flash(f'Erro {response.status_code} ao consultar o CNPJ {cnpj}. Verifique se está correto ou tente mais tarde.')
                return redirect('/cadastro')

            dados = response.json()

            if dados.get('descricao_situacao_cadastral', '').upper() != 'ATIVA':
                flash(f'CNPJ inválido. Situação atual: {dados.get("descricao_situacao_cadastral", "Não informada")}')
                return redirect('/cadastro')

            cnae_fiscal_api = dados.get('cnae_fiscal')
            if cnae_fiscal_api != 4520001:
                flash(f'CNAE ({cnae_fiscal_api}) não corresponde a serviços de mecânica (4520001).')
                return redirect('/cadastro')

            data_inicio_str = dados.get('data_inicio_atividade')
            if not data_inicio_str:
                flash('Data de início de atividade não encontrada para o CNPJ.')
                return redirect('/cadastro')

            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato inválido para data de início de atividade do CNPJ.')
                return redirect('/cadastro')

            hoje = datetime.today().date()
            meses_ativos = (hoje.year - data_inicio.year) * 12 + hoje.month - data_inicio.month
            if hoje.day < data_inicio.day:
                meses_ativos -= 1

            if meses_ativos < 3:
                flash(f'CNPJ precisa estar ativo há pelo menos 3 meses. Ativo há {meses_ativos} mes(es).')
                return redirect('/cadastro')

            if not dados.get('logradouro') or not dados.get('numero') or not dados.get('cep') or not dados.get('municipio') or not dados.get('uf'):
                flash('Endereço da empresa está incompleto na consulta do CNPJ.')
                return redirect('/cadastro')

            endereco = f"{dados.get('logradouro', '')}, {dados.get('numero', '')} - {dados.get('bairro', '')}, {dados.get('municipio', '')}/{dados.get('uf', '')}, CEP: {dados.get('cep', '')}"

            telefone_api = dados.get('ddd_telefone_1') or dados.get('ddd_telefone_2')
            if not celular_formatado and telefone_api:
                try:
                    telefone_api_limpo = "".join(filter(str.isdigit, telefone_api))
                    if len(telefone_api_limpo) >= 10:
                        parsed_api_phone = phonenumbers.parse(telefone_api_limpo, 'BR')
                        if phonenumbers.is_valid_number(parsed_api_phone):
                            celular_formatado = phonenumbers.format_number(parsed_api_phone, phonenumbers.PhoneNumberFormat.E164)
                            celular = phonenumbers.format_number(parsed_api_phone, phonenumbers.PhoneNumberFormat.NATIONAL)
                            flash('Celular preenchido e formatado com dados do CNPJ.')
                except phonenumbers.phonenumberutil.NumberParseException:
                    flash('Telefone do CNPJ não pôde ser formatado, usando o fornecido pelo usuário.')

            email_api = dados.get('email')
            if not email and email_api:
                email = email_api
                flash('E-mail preenchido com dados do CNPJ.')

            if db:
                try:
                    cursor = db.cursor()
                    cursor.execute('SELECT * FROM usuario WHERE cnpj = ?', (cnpj,))
                    existente_cnpj = cursor.fetchone()
                    if existente_cnpj:
                        flash('Este CNPJ já está cadastrado.')
                        return redirect('/cadastro')
                except Exception as e:
                    flash(f"Erro ao verificar CNPJ existente no banco de dados: {str(e)}")
                    return redirect('/cadastro')

        except Exception as e:
            traceback.print_exc()
            flash(f'Erro na validação do CNPJ: {str(e)}')
            return redirect('/cadastro')

    # ⚠️ NÃO insere ainda — aguarda verificação do e-mail
    session['codigo_verificacao'] = random.randint(1000, 9999)
    session['cadastro'] = {
        'nome': nome,
        'senha': senha,
        'email': email,
        'celular': celular_formatado,
        'tema': tema,
        'img_capa': img_capa,
        'img_perfil': img_perfil,
        'tipo': tipo,
        'cnpj': cnpj,
        'endereco': endereco
    }

    enviar_email_verificacao(email, session['codigo_verificacao'])
    return redirect('/verificacao_email')


@app.route('/avaliar', methods=['POST'])
def avaliar():
    try:
        data = request.get_json()
        nota = data.get('nota')
        usuario_id = data.get('usuarioId')
        avaliador_id = session.get('id')

        if None in (nota, usuario_id, avaliador_id):
            return jsonify({'error': 'Todos os campos são obrigatórios.'}), 400

        nota = int(nota)
        usuario_id = int(usuario_id)

        if not (0 <= nota <= 5):
            return jsonify({'error': 'Nota fora do intervalo permitido (0-5).'}), 400

        db = get_db()
        c = db.cursor()

        c.execute('SELECT 1 FROM avaliacoes WHERE usuario_id = ? AND avaliador_id = ?', (usuario_id, avaliador_id))
        if c.fetchone():
            return jsonify({'error': 'Você já avaliou esse mecânico.'}), 400

        c.execute('INSERT INTO avaliacoes (usuario_id, avaliador_id, nota) VALUES (?, ?, ?)', (usuario_id, avaliador_id, nota))
        db.commit()

        return jsonify({'mensagem': 'Avaliação registrada com sucesso.'}), 201
    except Exception as e:
        print(f'Erro ao avaliar: {e}')
        return jsonify({'error': 'Erro interno no servidor.'}), 500

@app.route('/media/<int:usuario_id>')
def media_por_usuario(usuario_id):
    db = get_db()  # Seu método que retorna conexão SQLite
    media = db.execute('SELECT AVG(nota) AS media FROM avaliacoes WHERE usuario_id = ?', (usuario_id,)).fetchone()
    media_valor = round(media['media'], 2) if media['media'] is not None else 0
    return jsonify({'media': media_valor})


@app.route("/verificacao_email", methods=["GET", "POST"])
def verificacao_email():
    if request.method == "POST":
        codigo_digitado = request.form.get("codigo")
        if 'codigo_verificacao' in session and str(session['codigo_verificacao']) == codigo_digitado:
            db = get_db()
            senha_hash = generate_password_hash(session['cadastro']['senha'])

            cursor = db.execute('''
                INSERT INTO usuario (nome, senha, tema, img_perfil, img_capa, email, celular, tipo, cnpj)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session['cadastro']['nome'],
                senha_hash,
                session['cadastro']['tema'],
                session['cadastro']['img_perfil'],
                session['cadastro']['img_capa'],
                session['cadastro']['email'],
                session['cadastro']['celular'],
                session['cadastro']['tipo'],
                session['cadastro'].get('cnpj', None)
            ))
            db.commit()
            session['id'] = cursor.lastrowid
            session.pop('cadastro', None)
            session.pop('codigo_verificacao', None)
            flash("Cadastro confirmado com sucesso!")
            return redirect("/home")
        else:
            flash("Código incorreto. Tente novamente.")
            return redirect("/verificacao_email")
    return render_template("verificacao_email.html")

@app.route("/home")
def home():
    if 'id' in session:
        db = get_db()
        usuario = db.execute('SELECT * FROM usuario WHERE id = ?', (session['id'],)).fetchone()
        if usuario:
            return render_template('home.html',
                               nome=usuario['nome'],
                               tema=usuario['tema'],
                               img_capa=usuario['img_capa'],
                               img_perfil=usuario['img_perfil'])
        else:
            flash('Usuário não encontrado...')
    return redirect('/')

@app.route("/perfil")
def perfil():
    if 'id' in session:
        db = get_db()
        usuario = db.execute('SELECT * FROM usuario WHERE id = ?', (session['id'],)).fetchone()
        if usuario:
            # Passa o objeto completo como 'user'
            return render_template('perfil.html', user=usuario)
        else:
            flash("Usuário não encontrado.")
            return redirect('/')
    flash("Você precisa estar logado.")
    return redirect('/')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'foto_perfil' not in request.files:
        flash('Nenhuma imagem foi enviada.')
        return redirect('/perfil')

    file = request.files['foto_perfil']

    if file.filename == '' or not allowed_file(file.filename):
        flash('Nome de arquivo inválido ou tipo não permitido.')
        return redirect('/perfil')

    if 'id' not in session:
        flash('Usuário não autenticado.')
        return redirect('/login')

    filename = secure_filename(f"perfil_{session['id']}_{file.filename}")
    upload_folder = app.config['UPLOAD_FOLDER']

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    caminho = os.path.join(upload_folder, filename)

    try:
        file.save(caminho)
        db = get_db()
        db.execute('UPDATE usuario SET img_perfil = ? WHERE id = ?', (f'/static/uploads/{filename}', session['id']))
        db.commit()
        flash('Foto de perfil atualizada com sucesso!')
    except Exception as e:
        flash(f'Erro ao atualizar foto: {e}')

    return redirect('/perfil')

@app.route("/chat")
def chat():
    if 'id' not in session:
        return redirect('/')
    
    db = get_db()
    usuario = db.execute('SELECT * FROM usuario WHERE id = ?', (session['id'],)).fetchone()
    if not usuario:
        return redirect('/')
    
    return render_template("chat.html", nome_usuario=usuario['nome'])

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/contatos')
def listar_contatos():
    if 'id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    db = get_db()
    
    # Lista de contatos adicionados
    contatos = db.execute('''
        SELECT u.id, u.nome, u.img_perfil, c.apelido 
        FROM contatos c
        JOIN usuario u ON c.contato_id = u.id
        WHERE c.usuario_id = ?
    ''', (session['id'],)).fetchall()
    
    # Sugestões de contatos (exceto os já adicionados e o próprio usuário)
    sugestoes = db.execute('''
        SELECT id, nome, img_perfil FROM usuario
        WHERE id NOT IN (
            SELECT contato_id FROM contatos WHERE usuario_id = ?
        ) AND id != ?
        LIMIT 10
    ''', (session['id'], session['id'])).fetchall()
    
    return jsonify({
        'contatos': [dict(c) for c in contatos],
        'sugestoes': [dict(s) for s in sugestoes]
    })

@app.route('/adicionar_contato/<int:usuario_id>', methods=['POST'])
def adicionar_contato(usuario_id):
    if 'id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    if usuario_id == session['id']:
        return jsonify({'error': 'Não é possível adicionar a si mesmo'}), 400

    db = get_db()
    # Verifica se o usuário a ser adicionado existe
    contato_existe = db.execute('SELECT id FROM usuario WHERE id = ?', (usuario_id,)).fetchone()
    if not contato_existe:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    try:
        # Adiciona o contato nos dois sentidos
        db.execute('INSERT OR IGNORE INTO contatos (usuario_id, contato_id) VALUES (?, ?)', 
                 (session['id'], usuario_id))
        db.execute('INSERT OR IGNORE INTO contatos (usuario_id, contato_id) VALUES (?, ?)', 
                 (usuario_id, session['id']))
        db.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Contato já existe'}), 400

@app.route('/iniciar_chat_privado/<int:outro_usuario_id>')
def iniciar_chat_privado(outro_usuario_id):
    if 'id' not in session:
        return jsonify({'success': False, 'error': 'Não autorizado'}), 401
    
    if outro_usuario_id == session['id']:
        return jsonify({'success': False, 'error': 'Não é possível conversar consigo mesmo'}), 400
    
    db = get_db()
    
    try:
        # Verifica se o outro usuário existe
        outro_usuario = db.execute('SELECT id FROM usuario WHERE id = ?', (outro_usuario_id,)).fetchone()
        if not outro_usuario:
            return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404

        # Verifica se já são contatos (em qualquer direção)
        sao_contatos = db.execute('''
            SELECT 1 FROM contatos 
            WHERE (usuario_id = ? AND contato_id = ?)
            OR (usuario_id = ? AND contato_id = ?)
        ''', (session['id'], outro_usuario_id, outro_usuario_id, session['id'])).fetchone()

        if not sao_contatos:
            # Se não forem contatos, cria a relação nos dois sentidos
            db.execute('INSERT OR IGNORE INTO contatos (usuario_id, contato_id) VALUES (?, ?)',
                     (session['id'], outro_usuario_id))
            db.execute('INSERT OR IGNORE INTO contatos (usuario_id, contato_id) VALUES (?, ?)',
                     (outro_usuario_id, session['id']))
            db.commit()

        # Verifica se já existe uma sala entre esses usuários
        sala_existente = db.execute('''
            SELECT uuid FROM salas_privadas
            WHERE (usuario1_id = ? AND usuario2_id = ?)
            OR (usuario1_id = ? AND usuario2_id = ?)
        ''', (session['id'], outro_usuario_id, outro_usuario_id, session['id'])).fetchone()

        if sala_existente:
            uuid_sala = sala_existente['uuid']
        else:
            # Cria nova sala com UUID único
            uuid_sala = str(uuid.uuid4())
            # Ordena os IDs para evitar duplicatas
            id1, id2 = sorted([session['id'], outro_usuario_id])
            db.execute('''
                INSERT INTO salas_privadas (uuid, usuario1_id, usuario2_id)
                VALUES (?, ?, ?)
            ''', (uuid_sala, id1, id2))
            db.commit()

        # Obtém informações completas do outro usuário
        outro_usuario_info = db.execute('''
            SELECT id, nome, img_perfil FROM usuario WHERE id = ?
        ''', (outro_usuario_id,)).fetchone()

        return jsonify({
            'success': True,
            'sala_uuid': uuid_sala,
            'outro_usuario': dict(outro_usuario_info)
        })

    except sqlite3.Error as e:
        db.rollback()
        print(f"Erro no banco de dados: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro no banco de dados',
            'details': str(e)
        }), 500
        
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao iniciar conversa privada',
            'details': str(e)
        }), 500

# Handlers do Socket.IO
@socketio.on('join_room')
def handle_join_room(data):
    if 'id' not in session:
        return
    
    room = data.get('room')
    join_room(room)
    emit('status', {'msg': f'Entrou na sala {room}'}, room=room)

@socketio.on('send_message')
def handle_send_message(data):
    if 'id' not in session:
        emit('error', {'message': 'Não autorizado'})
        return

    room = data.get('room')
    message = data.get('message', '').strip()

    if not message or not room:
        emit('error', {'message': 'Dados incompletos'})
        return

    db = get_db()

    try:
        # Verifica permissão para sala privada
        if room != 'principal':
            sala = db.execute('''
                SELECT 1 FROM salas_privadas 
                WHERE uuid = ? AND (usuario1_id = ? OR usuario2_id = ?)
            ''', (room, session['id'], session['id'])).fetchone()

            if not sala:
                emit('error', {'message': 'Você não tem permissão nesta sala'})
                return

        # Busca tipo de usuário (cliente ou mecanico)
        usuario = db.execute('''
            SELECT nome, img_perfil, tipo FROM usuario WHERE id = ?
        ''', (session['id'],)).fetchone()

        if not usuario:
            emit('error', {'message': 'Usuário não encontrado'})
            return

        # Bloquear links para clientes
        if usuario['tipo'] == 'cliente':
            url_pattern = re.compile(r'https?://\S+')
            if url_pattern.search(message):
                emit('error', {'message': 'Envio de links não permitido para clientes'})
                return

        # Insere mensagem no banco
        cursor = db.execute('''
            INSERT INTO mensagens (usuario_id, mensagem, sala_uuid)
            VALUES (?, ?, ?)
        ''', (session['id'], message, room))
        db.commit()

        # Prepara dados da mensagem para enviar ao frontend
        msg_data = {
            'id': cursor.lastrowid,
            'sender_id': session['id'],
            'sender_name': usuario['nome'],
            'sender_img': usuario['img_perfil'],
            'message': message,
            'time': datetime.now().strftime('%H:%M'),
            'room': room
        }

        emit('new_message', msg_data, room=room)

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        emit('error', {'message': 'Erro ao processar mensagem'})



@app.route('/perfil_data')
def perfil_data():
    if 'id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    db = get_db()
    usuario = db.execute('SELECT id, nome, img_perfil FROM usuario WHERE id = ?', (session['id'],)).fetchone()
    
    if not usuario:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    return jsonify(dict(usuario))

@app.route('/conversations')
def listar_conversas():
    if 'id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    db = get_db()
    
    try:
        # Obtém todas as conversas privadas do usuário
        conversas = db.execute('''
            SELECT sp.uuid, 
                   CASE WHEN sp.usuario1_id = ? THEN u2.id ELSE u1.id END as other_user_id,
                   CASE WHEN sp.usuario1_id = ? THEN u2.nome ELSE u1.nome END as other_user_nome,
                   CASE WHEN sp.usuario1_id = ? THEN u2.img_perfil ELSE u1.img_perfil END as other_user_img,
                   (SELECT m.mensagem FROM mensagens m 
                    WHERE m.sala_uuid = sp.uuid 
                    ORDER BY m.timestamp DESC LIMIT 1) as last_message,
                   (SELECT m.timestamp FROM mensagens m 
                    WHERE m.sala_uuid = sp.uuid 
                    ORDER BY m.timestamp DESC LIMIT 1) as last_message_time
            FROM salas_privadas sp
            JOIN usuario u1 ON sp.usuario1_id = u1.id
            JOIN usuario u2 ON sp.usuario2_id = u2.id
            WHERE sp.usuario1_id = ? OR sp.usuario2_id = ?
            ORDER BY last_message_time DESC
        ''', (session['id'], session['id'], session['id'], session['id'], session['id'])).fetchall()
        
        return jsonify([dict(c) for c in conversas])
        
    except Exception as e:
        print(f"Erro em /conversations: {str(e)}")
        return jsonify({'error': 'Erro ao carregar conversas'}), 500

@app.route('/get_chat_history/<room_id>')
def get_chat_history(room_id):
    if 'id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    db = get_db()
    
    try:
        # Verificação simplificada de permissão
        if room_id != 'principal':
            permissao = db.execute('''
                SELECT 1 FROM salas_privadas
                WHERE uuid = ? AND (usuario1_id = ? OR usuario2_id = ?)
            ''', (room_id, session['id'], session['id'])).fetchone()
            
            if not permissao:
                return jsonify({'error': 'Acesso não autorizado'}), 403

        # Query simplificada sem DISTINCT para melhor performance
        mensagens = db.execute('''
            SELECT m.id, m.usuario_id, u.nome as sender_name, 
                   u.img_perfil as sender_img, m.mensagem, m.timestamp
            FROM mensagens m
            JOIN usuario u ON m.usuario_id = u.id
            WHERE m.sala_uuid = ?
            ORDER BY m.timestamp ASC
        ''', (room_id,)).fetchall()
        
        return jsonify([dict(msg) for msg in mensagens])
        
    except Exception as e:
        print(f"Erro ao buscar histórico: {str(e)}")
        return jsonify({'error': 'Erro ao carregar histórico'}), 500
    
@app.route('/perfil/<int:user_id>')
def visualizar_perfil(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM usuario WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        return "Usuário não encontrado", 404
    return render_template('perfil.html', user=user)

@app.route("/configuracoes")
def configuracoes():
    return render_template('configuracoes.html')

@app.route('/alterar_senha', methods=['POST'])
def alterar_senha():
    if 'id' not in session:
        return jsonify({"erro": "Você precisa estar logado."}), 401

    dados = request.get_json()
    senha_atual = dados.get('senhaAtual')
    nova_senha = dados.get('novaSenha')
    confirma_senha = dados.get('confirmaSenha')

    if not senha_atual or not nova_senha or not confirma_senha:
        return jsonify({'erro': 'Preencha todos os campos.'}), 400

    db = get_db()
    usuario = db.execute('SELECT * FROM usuario WHERE id = ?', (session['id'],)).fetchone()

    if not check_password_hash(usuario['senha'], senha_atual):
        return jsonify({'erro': 'Senha atual incorreta.'}), 401

    if nova_senha != confirma_senha:
        return jsonify({'erro': 'As senhas não coincidem.'}), 400

    nova_hash = generate_password_hash(nova_senha)
    db.execute('UPDATE usuario SET senha = ? WHERE id = ?', (nova_hash, session['id']))
    db.commit()

    return jsonify({'mensagem': 'Senha alterada com sucesso!'}), 200

@app.route("/alterar_usuario", methods=["POST"])
def alterar_usuario():
    if 'id' not in session:
        return jsonify({"erro": "Você precisa estar logado."}), 401

    dados = request.get_json()
    novo_nome = dados.get("nome")  

    if not novo_nome or len(novo_nome) < 3:
        return jsonify({"erro": "Nome inválido."}), 400

    db = get_db()
    db.execute("UPDATE usuario SET nome = ? WHERE id = ?", (novo_nome, session["id"]))
    db.commit()

    return jsonify({"mensagem": "Nome de usuário alterado com sucesso!"}), 200

@app.route('/alterar_email', methods=['POST'])
def alterar_email():
    if 'id' not in session:
        return jsonify({"erro": "Você precisa estar logado."}), 401

    dados = request.get_json()
    novo_email = dados.get('novoEmail')
    confirma_email = dados.get('confirmaEmail')

    if not novo_email or not confirma_email:
        return jsonify({'erro': 'Preencha todos os campos.'}), 400

    if novo_email != confirma_email:
        return jsonify({'erro': 'Os e-mails não coincidem.'}), 400

    db = get_db()
    db.execute('UPDATE usuario SET email = ? WHERE id = ?', (novo_email, session['id']))
    db.commit()

    return jsonify({'mensagem': 'E-mail atualizado com sucesso!'}), 200

@app.route('/alterar_numero', methods=['POST'])
def alterar_numero():
    if 'id' not in session:
        return jsonify({"erro": "Você precisa estar logado."}), 401

    dados = request.get_json()
    novo_numero = dados.get('novoNumero')

    if not novo_numero:
        return jsonify({'erro': 'Informe um número de telefone.'}), 400

    if not celular_valido(novo_numero):
        return jsonify({'erro': 'Número inválido. Use o formato com DDD, ex: (11) 91234-5678.'}), 400

    parsed = phonenumbers.parse(novo_numero, 'BR')
    celular_formatado = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    db = get_db()
    db.execute('UPDATE usuario SET celular = ? WHERE id = ?', (celular_formatado, session['id']))
    db.commit()

    return jsonify({'mensagem': 'Número atualizado com sucesso!'}), 200

@app.route('/alterar_endereco', methods=['POST'])
def alterar_endereco():
    if 'id' not in session:
        return jsonify({"erro": "Você precisa estar logado."}), 401

    dados = request.get_json()
    novo_endereco = dados.get('novoEndereco')

    if not novo_endereco:
        return jsonify({'erro': 'Informe um endereço.'}), 400

    db = get_db()
    db.execute('UPDATE usuario SET endereco = ? WHERE id = ?', (novo_endereco, session['id']))
    db.commit()

    return jsonify({'mensagem': 'Endereço atualizado com sucesso!'}), 200

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/esquecer", methods=["GET", "POST"])
def esquecer():
    if request.method == "POST":
        email = request.form.get('email')
        flash('Se o email estiver cadastrado, enviaremos as instruções para alterar a senha.')
        return redirect(url_for('esquecer'))
    return render_template('esquecer.html')

@app.route("/mapa")
def mapa():
    endereco = request.args.get('endereco')
    return render_template('mapa.html', endereco=endereco)

# Google login
google_bp = make_google_blueprint(
    client_id="234929495058-irerg45sqm7rq9pgt0lrcm58qet3pico.apps.googleusercontent.com",
    client_secret="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",
    redirect_to="google_login_callback",
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"
    ]
)
app.register_blueprint(google_bp, url_prefix="/google_login")

@app.route("/google_login/callback")
def google_login_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Falha ao obter informações do usuário do Google.", "error")
        return redirect(url_for("login"))

    user_info = resp.json()
    email = user_info["email"]
    nome = user_info.get("name", email.split("@")[0])

    db = get_db()
    usuario = db.execute('SELECT * FROM usuario WHERE email = ?', (email,)).fetchone()

    if not usuario:
        senha_hash = generate_password_hash("senha_google")
        cursor = db.execute('INSERT INTO usuario (nome, senha, email, tipo) VALUES (?, ?, ?, ?)', (nome, senha_hash, email, 'cliente'))
        db.commit()
        usuario_id = cursor.lastrowid
    else:
        usuario_id = usuario['id']

    session['id'] = usuario_id
    flash(f"Bem-vindo, {nome}!")
    return redirect(url_for("home"))

if __name__ == '__main__':
    socketio.run(app, debug=True)