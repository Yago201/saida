from flask import Blueprint, request, jsonify, send_file
from database import get_connection
from io import BytesIO
import openpyxl
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from mysql.connector.errors import IntegrityError

ponto_bp = Blueprint('ponto', __name__)

# Registrar entrada
@ponto_bp.route('/entrada', methods=['POST'])
def registrar_entrada():
    data = request.get_json()
    funcionario_id = data.get('funcionario_id')

    if not funcionario_id:
        return jsonify({'error': 'ID do funcionário é obrigatório'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT nome FROM funcionarios WHERE id = %s", (funcionario_id,))
    funcionario = cursor.fetchone()
    if not funcionario:
        cursor.close()
        conn.close()
        return jsonify({'error': f'Funcionário ID {funcionario_id} não encontrado.'}), 404

    nome = funcionario['nome']

    cursor = conn.cursor()
    cursor.execute("INSERT INTO registros_ponto (funcionario_id, nome, horario_entrada) VALUES (%s, %s, NOW())", (funcionario_id, nome))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': f'Entrada registrada com sucesso para {nome}!'})

# Registrar saída
@ponto_bp.route('/saida', methods=['POST'])
def registrar_saida():
    data = request.get_json()
    funcionario_id = data.get('funcionario_id')

    if not funcionario_id:
        return jsonify({'error': 'ID do funcionário é obrigatório'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE registros_ponto
        SET horario_saida = NOW()
        WHERE funcionario_id = %s AND horario_saida IS NULL
        ORDER BY horario_entrada DESC
        LIMIT 1
    """, (funcionario_id,))
    conn.commit()
    rows = cursor.rowcount
    cursor.close()
    conn.close()

    if rows == 0:
        return jsonify({'error': 'Nenhuma entrada encontrada para esse funcionário'}), 404

    return jsonify({'message': 'Saída registrada com sucesso!'})

# Cadastrar funcionário
@ponto_bp.route('/funcionarios', methods=['POST'])
def cadastrar_funcionario():
    data = request.get_json()
    id = data.get('id')
    nome = data.get('nome')

    if not id or not nome:
        return jsonify({'error': 'ID e nome são obrigatórios'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO funcionarios (id, nome) VALUES (%s, %s)", (id, nome))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Funcionário cadastrado com sucesso!'})
    except IntegrityError:
        return jsonify({'error': f'Funcionário com ID {id} já existe.'}), 409

# Listar funcionários
@ponto_bp.route('/funcionarios', methods=['GET'])
def listar_funcionarios():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nome FROM funcionarios ORDER BY nome ASC")
    funcionarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(funcionarios)

# Listar registros com filtro por data (com JOIN para mostrar nomes)
@ponto_bp.route('/registros', methods=['GET'])
def listar_registros():
    data_param = request.args.get('data')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if data_param:
        cursor.execute("""
            SELECT rp.funcionario_id, f.nome, rp.horario_entrada, rp.horario_saida
            FROM registros_ponto rp
            LEFT JOIN funcionarios f ON rp.funcionario_id = f.id
            WHERE DATE(rp.horario_entrada) = %s
            ORDER BY rp.horario_entrada DESC
        """, (data_param,))
    else:
        cursor.execute("""
            SELECT rp.funcionario_id, f.nome, rp.horario_entrada, rp.horario_saida
            FROM registros_ponto rp
            LEFT JOIN funcionarios f ON rp.funcionario_id = f.id
            ORDER BY rp.horario_entrada DESC
        """)

    registros = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(registros)

# Listar nomes de funcionários cadastrados
@ponto_bp.route('/lista-funcionarios', methods=['GET'])
def listar_nomes_funcionarios():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nome FROM funcionarios ORDER BY nome ASC")
    funcionarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(funcionarios)

# Exportar Excel
@ponto_bp.route('/exportar-excel', methods=['GET'])
def exportar_excel():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registros_ponto ORDER BY horario_entrada DESC")
    registros = cursor.fetchall()
    cursor.close()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Nome", "Entrada", "Saída"])

    for r in registros:
        ws.append([
            r['funcionario_id'],
            r['nome'] or '',
            r['horario_entrada'] or '',
            r['horario_saida'] or ''
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name="registros.xlsx", as_attachment=True)

# Exportar PDF
@ponto_bp.route('/exportar-pdf', methods=['GET'])
def exportar_pdf():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registros_ponto ORDER BY horario_entrada DESC")
    registros = cursor.fetchall()
    cursor.close()
    conn.close()

    output = BytesIO()
    doc = SimpleDocTemplate(output)
    styles = getSampleStyleSheet()
    flowables = [Paragraph("Registros de Ponto", styles['Title']), Spacer(1, 12)]

    for r in registros:
        entrada = r['horario_entrada'] or '-'
        saida = r['horario_saida'] or '-'
        flowables.append(Paragraph(
            f"ID: {r['funcionario_id']} | Nome: {r['nome']}<br/>Entrada: {entrada} | Saída: {saida}",
            styles['Normal']
        ))
        flowables.append(Spacer(1, 12))

    doc.build(flowables)
    output.seek(0)
    return send_file(output, download_name="registros.pdf", as_attachment=True)
