import random
import string
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request
from sqlalchemy import select
from models import SessionLocalExemplo, Movimentacao, Encomenda, Cliente, Usuario, Galpao
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

app = Flask(__name__)

# definir a SENHA, em produção colocar em local seguro
app.config["JWT_SECRET_KEY"] = 'Ch@rl13_Br0wn_Jr'
jwt = JWTManager(app)


def shutdown_session(exception=None):
    db = SessionLocalExemplo()
    db.remove()
    db.close()

def load_user(id_u1):
    db = SessionLocalExemplo()
    user = select(Usuario).where(Usuario.id_usuario == int(id_u1))
    resultado = db.execute(user).scalar_one_or_none()
    db.close()
    return resultado

def gerar_codigo_random(tamanho=8):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(tamanho))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        print(f"User: {current_user}")
        db = SessionLocalExemplo()
        try:
            sql = select(Usuario).where(Usuario.email == current_user)
            sql_result = db.execute(sql).scalar()
            print('Usuario:', sql_result)
            if sql_result and sql_result.perfil == 'ADMIN':
                return fn(*args, **kwargs)
            dado = {
                "msg": "Acesso negado: Requer privilégio de administrador",
            }
            return jsonify(dado), 403
        except Exception as e:
            print(e)
        finally:
            db.close()

    return wrapper


@app.route("/get_encomenda", methods=["GET"])
def get_encomenda():
    """
      **API para Consulta de Encomendas**

      ### Endpoint:
      GET /get_encomenda

      ### Parametros de Entrada:
      Não possui parâmetros de entrada.

      ### Respostas (JSON):
      * **200 OK:** Lista de encomendas com seus respectivos clientes retornada com sucesso.
        ```json
        [
            {
                "encomenda": {
                    "id_encomenda": 1,
                    "descricao": "string",
                    "status_encomenda": "string",
                    "cliente_id": 1
                },
                "cliente": {
                    "id_cliente": 1,
                    "nome": "string",
                    "cpf": "string"
                }
            }
        ]
        ```
    """
    db = SessionLocalExemplo()
    try:
        sql_encomenda = select(Encomenda, Cliente).join(Cliente, Cliente.id_cliente == Encomenda.cliente_id)
        result_encomenda = db.execute(sql_encomenda).all()
        list_encomenda = []
        for encomenda, cliente in result_encomenda:
            dados = {
                "encomenda": encomenda.serialize(),
                "cliente": cliente.serialize(),
            }
            list_encomenda.append(dados)
        print(list_encomenda)
        return jsonify(list_encomenda), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
    finally:
        db.close()

@app.route("/get_movimentacao", methods=["GET"])
def get_movimentacao():
    """
      **API para Consulta de Movimentações**

      ### Endpoint:
      GET /get_movimentacao

      ### Parametros de Entrada:
      Não possui parâmetros de entrada.

      ### Respostas (JSON):
      * **200 OK:** Lista de movimentacoes (ordenada da mais recente para a mais antiga) com os dados de galpoes, encomendas e clientes atualizados.
        ```json
        [
            {
                "movimentacao": {
                    "id_movimentacao": 1,
                    "status_movimentacao": "string (ENTRADA/SAIDA)",
                    "data_atual": "string",
                    "encomenda_id": 1,
                    "galpao_id": 1
                },
                "galpoes": {
                    "id_galpao": 1,
                    "cidade": "string",
                    "estado": "string"
                },
                "encomendas": {
                    "id_encomenda": 1,
                    "status_encomenda": "string (CAMINHO/ENTREGUE/TRANSITO)"
                },
                "clientes": {
                    "id_cliente": 1,
                    "nome": "string",
                    "endereco": "string (cidade/estado)"
                }
            }
        ]
        ```
      * **500 Internal Server Error:** Falha operacional ao tentar verificar movimentacao.
        ```json
        {
            "msg": "Erro ao tentar verificar movimentacao"
        }
        ```
    """
    db = SessionLocalExemplo()
    try:
        sql_movimentacao = (select(Movimentacao, Galpao, Encomenda, Cliente)
                            .join(Encomenda, Movimentacao.encomenda_id == Encomenda.id_encomenda)
                            .join(Galpao, Movimentacao.galpao_id == Galpao.id_galpao)
                            .join(Cliente, Cliente.id_cliente == Encomenda.cliente_id)
                            .order_by(Movimentacao.data_atual.asc()))
        result_movi = db.execute(sql_movimentacao)
        list_movi = []

        for movi, galpoes, encomendas, clientes in result_movi:

            if movi.status_movimentacao == "ENTRADA" and f"{galpoes.cidade}/{galpoes.estado}" == clientes.endereco:
                encomendas.status_encomenda = "CAMINHO"

            elif movi.status_movimentacao == "SAIDA" and f"{galpoes.cidade}/{galpoes.estado}" == clientes.endereco:
                encomendas.status_encomenda = "ENTREGUE"

            elif encomendas.id_encomenda == movi.encomenda_id and f"{galpoes.cidade}/{galpoes.estado}" != clientes.endereco:
                encomendas.status_encomenda = "TRANSITO"

            m1, g1, e1, c1 = movi.serialize(), galpoes.serialize(), encomendas.serialize(), clientes.serialize()
            dados = {
                "movimentacao": m1,
                "galpoes": g1,
                "encomendas": e1,
                "clientes": c1
            }
            list_movi.append(dados)

        list_movi.reverse()
        db.commit()
        return jsonify(list_movi), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return jsonify({"msg": "Erro ao tentar verificar movimentacao"}), 500
    finally:
        db.close()

@app.route("/get_clientes", methods=["GET"])
def get_clientes():
    """
      **API para Consulta de Clientes**

      ### Endpoint:
      GET /get_clientes

      ### Parametros de Entrada:
      Não possui parâmetros de entrada.

      ### Respostas (JSON):
      * **200 OK:** Lista de clientes retornada com sucesso.
        ```json
        [
            {
                "id_cliente": 1,
                "nome": "string",
                "cpf": "string",
                "telefone": "string",
                "endereco": "string",
                "rua": "string",
                "numero_casa": "string"
            }
        ]
        ```
    """
    db = SessionLocalExemplo()
    try:
        sql_cliente = select(Cliente)
        result_cliente = db.execute(sql_cliente).scalars()
        list_cliente = []
        for cliente in result_cliente:
            list_cliente.append(cliente.serialize())
        return jsonify(list_cliente), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
    finally:
        db.close()

@app.route('/get_galpoes', methods=['GET'])
def get_galpoes():
    """
      **API para Consulta de Galpões**

      ### Endpoint:
      GET /get_galpoes

      ### Parametros de Entrada:
      Não possui parâmetros de entrada.

      ### Respostas (JSON):
      * **200 OK:** Lista de galpoes retornada com sucesso.
        ```json
        [
            {
                "id_galpao": 1,
                "cidade": "string",
                "estado": "string"
            }
        ]
        ```
      * **500 Internal Server Error:** Falha operacional no banco de dados.
        ```json
        {
            "error": "[Descricao do Erro]"
        }
        ```
    """
    db = SessionLocalExemplo()
    try:
        sql_galpao = select(Galpao)
        result_galpao = db.execute(sql_galpao).scalars()
        list_galpao = []
        for i in result_galpao:
            list_galpao.append(i.serialize())
        return jsonify(list_galpao), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@app.route("/post_usuario", methods=["POST"])
def post_usuario():
    """
        **API para Cadastro de Usuario**

        ### Endpoint:
        POST /post_usuario

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "nome": "string (obrigatorio) - Nome completo do usuario",
            "senha": "string (obrigatorio) - Senha para acesso ao sistema",
            "data_nascimento": "datetime (obrigatorio) - Data de nascimento formato YYYY-MM-DD",
            "email": "string (obrigatorio) - Endereco de e-mail do usuario",
            "perfil": "string (obrigatorio) - Perfil de acesso do usuario"
        }
        ```

        ### Respostas (JSON):
        * **200 Created:** Usuario registrado com sucesso.
          ```json
          {
              "msg": "Usuario cadastrado"
          }
          ```
        * **400 Bad Request:** Ausencia de campos obrigatorios.
          ```json
          {
              "msg": "Valor não Encontrado"
          }
          ```
        * **409 Conflict:** Usuario ja cadastrado com o e-mail fornecido.
          ```json
          {
              "msg": "Usuario já cadastrado"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao registrar usuário: [Descricao do Erro]"
          }
          ```
        """
    dados = request.get_json()
    nome = dados.get("nome")
    senha = dados.get("senha")
    data_nascimento = dados.get("data_nascimento")
    email = dados.get("email")
    perfil = dados.get("perfil")
    print(nome, email, senha, data_nascimento, perfil)
    if not nome or not senha or not email or not perfil or not data_nascimento:
        return jsonify({"msg": "Valor não Encontrado"}), 400
    data = datetime.strptime(data_nascimento, '%Y-%m-%d')
    db = SessionLocalExemplo()
    user_v = select(Usuario).where(Usuario.email == email)
    result_usuario = db.execute(user_v).first()

    if result_usuario:
        return jsonify({"msg": "Usuario já cadastrado"}), 409

    try:
        user = Usuario(nome=nome, email=email, data_nascimento=data, perfil=perfil)
        user.set_password(senha)
        db.add(user)
        db.commit()
        return jsonify({"msg": "Usuario cadastrado"}), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return jsonify({"msg": f"Erro ao registrar usuário: {str(e)}"}), 500
    finally:
        db.close()

@app.route("/logar_usuario", methods=["POST"])
def logar_usuario():
    """
        **API para Autenticacao de Usuario**

        ### Endpoint:
        POST /logar_usuario

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "email": "string (obrigatorio) - Endereco de e-mail do usuario",
            "senha": "string (obrigatorio) - Senha de acesso do usuario"
        }
        ```

        ### Respostas (JSON):
        * **200 OK:** Usuario autenticado com sucesso.
          ```json
          {
              "msg": "Usuario Logado com sucesso"
          }
          ```
        * **401 Unauthorized:** Credenciais invalidas ou incorretas.
          ```json
          {
              "msg": "Credenciais"
          }
          ```
        * **404 Not Found:** Ausencia de campos obrigatorios.
          ```json
          {
              "msg": "Valor não encontrado"
          }
          ```
        * **400 Bad Request:** Falha operacional ao processar a solicitacao.
          ```json
          {
              "msg": "[Descricao do Erro]"
          }
          ```
        """
    dados = request.get_json()
    email = dados.get("email")
    senha = dados.get("senha")
    if not email or not senha:
        return jsonify({"msg": "Valor não encontrado"}), 404
    db = SessionLocalExemplo()
    try:
        sql_user = select(Usuario).where(Usuario.email == email)
        usuario_existente = db.execute(sql_user).scalar_one_or_none()

        if usuario_existente and usuario_existente.check_password(senha):
            return jsonify({"msg": "Usuario Logado com sucesso"}), 200

        dados = {
            "msg": "Credenciais"
        }
        return jsonify(dados), 401
    except Exception as e:
        return jsonify({"msg": str(e)}), 400
    finally:
        db.close()

@app.route("/post_encomenda", methods=["POST"])
def post_encomenda():
    """
        **API para Cadastro de Encomenda**

        ### Endpoint:
        POST /post_encomenda

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "remetente": "string (obrigatorio) - Nome do remetente da encomenda",
            "cliente_id": "int (obrigatorio) - Identificador unico do cliente associado"
        }
        ```

        ### Respostas (JSON):
        * **200 Created:** Encomenda registrada com sucesso.
          ```json
          {
              "msg": "Encomenda cadastrada com sucesso"
          }
          ```
        * **400 Bad Request:** Ausencia de campos obrigatorios ou encomenda ja cadastrada.
          ```json
          {
              "msg": "Valor não Encontrado"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao registrar encomeda: [Descricao do Erro]"
          }
          ```
        """
    dados = request.get_json()
    remetente = dados.get("remetente")
    codigo_r = gerar_codigo_random(8)
    status = "POSTADO"
    cliente_id = dados.get("cliente_id")
    if not (remetente or cliente_id):
        return jsonify({"msg": "Valores Indefinidos","status": "danger"}), 400
    db = SessionLocalExemplo()
    sql_encomenda = select(Encomenda).where(Encomenda.codigo_r == codigo_r)
    result_encomenda = db.execute(sql_encomenda).scalar()

    if result_encomenda:
        return jsonify({"msg": "Encomenda já foi Cadastrado","status": "danger"}), 409

    try:
        encomenda = Encomenda(remetente=remetente, cliente_id=cliente_id, status_encomenda=status,
                              codigo_r=codigo_r)
        db.add(encomenda)
        db.commit()
        return jsonify({"msg": "Encomenda cadastrada com sucesso","status": "success"}), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return jsonify({"msg": f"Erro ao tentar Cadastrar encomeda: {str(e)}","status": "warning"}), 500
    finally:
        db.close()
        
@app.route('/pesquisar_encomenda', methods=['POST'])
def pesquisar_encomenda():
    """
        **API para Pesquisa de Encomenda**

        ### Endpoint:
        POST /pesquisar_encomenda

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "termo": "string (obrigatorio) - Codigo de rastreio da encomenda"
        }
        ```

        ### Respostas (JSON):
        * **200 OK:** Lista com o historico de rastreio e movimentacoes encontrado.
          ```json
          [
              {
                  "movimentacao": "object - Dados serializados da movimentacao",
                  "galpao": "object - Dados serializados do galpao",
                  "encomenda": "object - Dados serializados da encomenda",
                  "cliente": "object - Dados serializados do cliente"
              }
          ]
          ```
        * **200 OK (Vazio):** Codigo invalido ou nao fornecido.
          ```json
          {
              "msg": "Nenhuma encomenda encontrada"
          }
          ```
        * **400 Bad Request:** Falha operacional ao processar a pesquisa.
          ```json
          {
              "error": "[Descricao do Erro]"
          }
          ```
        """
    db = SessionLocalExemplo()
    dados = request.get_json()
    codigo = dados.get("termo")

    if codigo is None or codigo == "":
        return jsonify({"msg": "Nenhuma encomenda encontrada"})
    try:
        sql_busca = (select(Movimentacao, Galpao, Encomenda, Cliente)
                     .join(Encomenda, Movimentacao.encomenda_id == Encomenda.id_encomenda)
                     .join(Galpao, Movimentacao.galpao_id == Galpao.id_galpao)
                     .join(Cliente, Cliente.id_cliente == Encomenda.cliente_id)
                     .where(Encomenda.codigo_r == codigo)
                     .order_by(Movimentacao.data_atual.asc())
                     )
        rastreio = db.execute(sql_busca)
        lista_rastreio = []
        for movi, gal, enco, clie in rastreio:

            if movi.status_movimentacao == "ENTRADA" and f"{gal.cidade}/{gal.estado}" == clie.endereco:
                enco.status_encomenda = "CAMINHO"

            elif movi.status_movimentacao == "SAIDA" and f"{gal.cidade}/{gal.estado}" == clie.endereco:
                enco.status_encomenda = "ENTREGUE"

            elif enco.id_encomenda == movi.encomenda_id and f"{gal.cidade}/{gal.estado}" != clie.endereco:
                enco.status_encomenda = "TRANSITO"

            dados = {
                "movimentacao": movi.serialize(),
                "galpao": gal.serialize(),
                "encomenda": enco.serialize(),
                "cliente": clie.serialize()
            }
            lista_rastreio.append(dados)

        lista_rastreio.reverse()

        db.commit()
        return jsonify(lista_rastreio), 200
    except Exception as e:
        print(f'Erro ao pesquisar filme: {e}')
        db.rollback()
        return jsonify({"error": e}), 400
    finally:
        db.close()

@app.route("/post_movimentacao", methods=["POST"])
def post_movimentacao():
    """
        **API para Cadastro de Movimentacao**

        ### Endpoint:
        POST /post_movimentacao

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "galpao_id": "int/string (obrigatorio) - Identificador unico do galpao",
            "encomenda_id": "int/string (obrigatorio) - Identificador unico da encomenda"
        }
        ```

        ### Respostas (JSON):
        * **200 Created:** Movimentacao registrada com sucesso.
          ```json
          {
              "msg": "Movimentação cadastrado com sucesso"
          }
          ```
        * **200 OK:** Movimentacao ja registrada anteriormente para o mesmo galpao e status.
          ```json
          {
              "msg": "Movimentação já registrada"
          }
          ```
        * **400 Bad Request:** Ausencia de campos obrigatorios.
          ```json
          {
              "msg": "Valor não Encontrado"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao registrar movimentacao: [Descricao do Erro]"
          }
          ```
        """
    dados = request.get_json()
    galpao_id = dados.get("galpao_id")
    encomenda_id = dados.get("encomenda_id")

    if not galpao_id or not encomenda_id:
        return jsonify({"msg": "Valor não Encontrado"}), 400
    db = SessionLocalExemplo()

    sql_movi = select(Movimentacao).where(Movimentacao.encomenda_id == encomenda_id).order_by(
        Movimentacao.data_atual.desc())
    result_movi = db.execute(sql_movi).scalars().first()

    if result_movi:
        if result_movi.status_movimentacao == "ENTRADA":
            status = "SAIDA"
        else:
            status = "ENTRADA"
    else:
        status = "ENTRADA"

    print('new status', status)

    sql_veri_movi = (select(Movimentacao)
                     .where(Movimentacao.encomenda_id == encomenda_id)
                     .where(Movimentacao.galpao_id == galpao_id)
                     .where(Movimentacao.status_movimentacao == status)
                     )
    result_vm = db.execute(sql_veri_movi).scalars().first()

    print('result', result_vm)

    if result_vm:
        print("Movimentacao já cadastrada")
        return jsonify({"msg": "Movimentação já registrada"})

    try:
        encomenda = Movimentacao(galpao_id=int(galpao_id), encomenda_id=int(encomenda_id), status_movimentacao=status)
        db.add(encomenda)
        db.commit()
        return jsonify({"msg": "Movimentação cadastrado com sucesso"}), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return jsonify({"msg": f"Erro ao registrar movimentacao: {str(e)}"}), 500
    finally:
        db.close()

@app.route("/post_cliente", methods=["POST"])
def post_cliente():
    """
        **API para Cadastro de Cliente**

        ### Endpoint:
        POST /post_cliente

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "nome": "string (obrigatorio) - Nome do cliente",
            "cpf": "string (obrigatorio) - CPF unico do cliente",
            "telefone": "string (obrigatorio) - Telefone de contato",
            "endereco": "string (obrigatorio) - Cidade/Estado de destino do cliente",
            "rua": "string (obrigatorio) - Logradouro do cliente",
            "numero_casa": "string/int (obrigatorio) - Numero da residencia"
        }
        ```

        ### Respostas (JSON):
        * **200 Created:** Cliente registrado com sucesso.
          ```json
          {
              "msg": "Cliente cadastrado com sucesso"
          }
          ```
        * **400 Bad Request:** Ausencia de campos obrigatorios ou cliente ja cadastrado.
          ```json
          {
              "msg": "Valor não Encontrado"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao registrar cliente: [Descricao do Erro]"
          }
          ```
        """
    if request.method == "POST":
        dados = request.get_json()
        nome = dados.get("nome")
        cpf = dados.get("cpf")
        telefone = dados.get("telefone")
        endereco = dados.get("endereco")
        rua = dados.get("rua")
        numero_casa = dados.get("numero_casa")
        if not nome or not cpf or not telefone or not endereco or not rua or not numero_casa or endereco == "undefined/undefined" or rua == "undefined":
            return jsonify({"msg": "Valor não Encontrado","status": "danger"}), 400
        db = SessionLocalExemplo()
        sql_clie = select(Cliente).where(Cliente.cpf == cpf)
        result_clie = db.execute(sql_clie).first()

        if result_clie:
            return jsonify({"msg": "Cliente já foi Cadastrado","status": "danger"}), 409

        try:
            cliente = Cliente(nome=nome, cpf=cpf, telefone=telefone, endereco=endereco, rua=rua,
                              numero_casa=numero_casa)
            db.add(cliente)
            db.commit()
            return jsonify({"msg": "Cliente cadastrado com sucesso","status": "success"}), 200
        except Exception as e:
            db.rollback()
            print(f"ERROR: {e}")
            return jsonify({"msg": f"Erro ao registrar cliente: {str(e)}","status": "warning"}), 500
        finally:
            db.close()

@app.route('/post_galpao', methods=['POST'])
def post_galpao():
    """
        **API para Cadastro de Galpao**

        ### Endpoint:
        POST /post_galpao

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "cidade": "string (obrigatorio) - Cidade onde o galpao esta localizado",
            "estado": "string (obrigatorio) - Estado onde o galpao esta localizado"
        }
        ```

        ### Respostas (JSON):
        * **200 Created:** Galpao registrado com sucesso.
          ```json
          {
              "msg": "Galpão cadastrado com sucesso"
          }
          ```
        * **400 Bad Request:** Ausencia de campos obrigatorios ou galpao ja cadastrado.
          ```json
          {
              "msg": "Valores invalidos"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "[Descricao do Erro]"
          }
          ```
        """
    dados = request.get_json()
    cidade = dados.get("cidade")
    estado = dados.get("estado")
    if not (cidade or estado):
        print("valores invalidos")
        return jsonify({"msg": "Valores invalidos","status": "danger"}), 400
    db = SessionLocalExemplo()
    sql_galpa = select(Galpao).where(Galpao.cidade == cidade, Galpao.estado == estado)
    result_galpa = db.execute(sql_galpa).first()
    if result_galpa:
        return jsonify({"msg": "Galpao já foi Cadastrado","status": "danger"}), 409
    try:
        galpao = Galpao(cidade=cidade, estado=estado)
        db.add(galpao)
        db.commit()
        return jsonify({"msg": "Galpão cadastrado com sucesso","status": "success"}), 200
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return jsonify({"msg": f"Erro ao atualizar Galpão: {str(e)}","status":"warning"}), 500
    finally:
        db.close()


@app.route('/put_user/<var_id>', methods=['PUT'])
def put_user(var_id):
    """
        **API para Edição de Usuário**

        ### Endpoint:
        PUT /put_user

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "nome": "string (obrigatorio) - Novo nome do usuario",
            "email": "string (obrigatorio) - Novo endereco de e-mail",
            "data_nasc": "string (obrigatorio) - Nova data de nascimento",
            "perfil": "string (obrigatorio) - Novo perfil de acesso"
        }
        ```

        ### Respostas (JSON):
        * **200 OK:** Usuário atualizado com sucesso.
          ```json
          {
              "msg": "User atualizado com sucesso"
          }
          ```
        * **400 Bad Request:** Ausência de campos obrigatórios.
          ```json
          {
              "msg": "Valor invalido"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao atualizar user: [Descricao do Erro]"
          }
          ```
        """
    db = SessionLocalExemplo()
    editar_user = select(Usuario).where(Usuario.id_usuario == int(var_id))
    result_user = db.execute(editar_user).scalar_one_or_none()
    if request.method == "PUT":
        dados = request.get_json()
        nome = dados.get("nome")
        email = dados.get("email")
        data_nasc = dados.get("data_nasc")
        perfil = dados.get("perfil")
        if not (nome or email or data_nasc or perfil):
            return jsonify({"msg": "Valor invalido"}), 400
        try:
            result_user.nome = nome
            result_user.email = email
            result_user.data_nasc = data_nasc
            result_user.perfil = perfil
            db.commit()
            return jsonify({"msg": "User atualizado com sucesso"}), 200
        except Exception as e:
            db.rollback()
            print(f"ERROR: {e}")
            return jsonify({"msg": f"Erro ao atualizar user: {str(e)}"})
        finally:
            db.close()

@app.route("/put_cliente/<var_id>", methods=["PUT"])
def put_cliente(var_id):
    """
        **API para Edição de Cliente**

        ### Endpoint:
        PUT /put_cliente

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "nome": "string (obrigatorio) - Novo nome do cliente",
            "cpf": "string (obrigatorio) - Novo CPF do cliente",
            "telefone": "string (obrigatorio) - Novo telefone de contato",
            "endereco": "string (obrigatorio) - Novo endereco do cliente",
            "rua": "string (obrigatorio) - Nova rua do cliente",
            "numero_casa": "string/int (obrigatorio) - Novo numero da residencia"
        }
        ```

        ### Respostas (JSON):
        * **200 OK:** Cliente atualizado com sucesso.
          ```json
          {
              "msg": "Cliente atualizado com sucesso"
          }
          ```
        * **400 Bad Request:** Ausência de campos obrigatórios.
          ```json
          {
              "msg": "Valores Indefinidos"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao atualizar cliente: [Descricao do Erro]"
          }
          ```
        """
    db = SessionLocalExemplo()
    editar_cliente = select(Cliente).where(Cliente.id_cliente == int(var_id))
    result_cliente = db.execute(editar_cliente).scalar_one_or_none()
    if request.method == "PUT":
        dados = request.get_json()
        nome = dados.get("nome")
        cpf = dados.get("cpf")
        telefone = dados.get("telefone")
        endereco = dados.get("endereco")
        rua = dados.get("rua")
        numero_casa = dados.get("numero_casa")
        print(nome,cpf,telefone,endereco,rua,numero_casa)
        if not nome or not cpf or not telefone or not endereco or not rua or not numero_casa or endereco == "undefined/undefined" or rua == "undefined":
            return jsonify({"msg": "Valores Indefinidos","status": "danger"}), 400

        try:
            result_cliente.nome = nome
            result_cliente.cpf = cpf
            result_cliente.telefone = telefone
            result_cliente.endereco = endereco
            result_cliente.rua = rua
            result_cliente.numero_casa = numero_casa
            db.commit()
            return jsonify({"msg": "Cliente atualizado com sucesso","status": "success"}), 200
        except Exception as e:
            db.rollback()
            print(f"ERROR: {e}")
            return jsonify({"msg": f"Erro ao atualizar cliente: {str(e)}","status": "warning"})
        finally:
            db.close()

@app.route("/put_encomenda/<var_id>", methods=["PUT"])
def put_encomenda(var_id):
    """
        **API para Edição de Encomenda**

        ### Endpoint:
        PUT /put_encomenda

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "remetente": "string (obrigatorio) - Novo nome ou descricao do remetente"
        }
        ```

        ### Respostas (JSON):
        * **200 OK:** Encomenda atualizada com sucesso.
          ```json
          {
              "msg": "Encomenda atualizada com sucesso"
          }
          ```
        * **400 Bad Request:** Ausência de campos obrigatórios.
          ```json
          {
              "msg": "Valores Indefinidos"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao atualizar Encomenda: [Descricao do Erro]"
          }
          ```
        """
    db = SessionLocalExemplo()
    editar_encom = select(Encomenda).where(Encomenda.id_encomenda == int(var_id))
    result_enco = db.execute(editar_encom).scalar_one_or_none()
    if request.method == "PUT":
        dados = request.get_json()
        remetente = dados.get("remetente")
        if not remetente:
            return jsonify({"msg": "Valores Indefinidos"}), 400
        try:
            result_enco.remetente = remetente
            db.commit()
            return jsonify({"msg": "Encomenda atualizada com sucesso"}), 200
        except Exception as e:
            db.rollback()
            print(f"ERROR: {e}")
            return jsonify({"msg": f"Erro ao atualizar Encomenda: {str(e)}"})
        finally:
            db.close()

@app.route("/put_galpao/<var_id>", methods=["PUT"])
def put_galpao(var_id):
    """
        **API para Edição de Galpão**

        ### Endpoint:
        PUT /put_galpao

        ### Parâmetros de Entrada (JSON):
        ```json
        {
            "cidade": "string (obrigatorio) - Nova cidade do galpao",
            "estado": "string (obrigatorio) - Novo estado do galpao"
        }
        ```

        ### Respostas (JSON):
        * **200 OK:** Galpão atualizado com sucesso.
          ```json
          {
              "msg": "Galpão atualizado com sucesso"
          }
          ```
        * **400 Bad Request:** Ausência de campos obrigatórios.
          ```json
          {
              "msg": "Valores Indefinidos"
          }
          ```
        * **500 Internal Server Error:** Falha operacional no banco de dados.
          ```json
          {
              "msg": "Erro ao atualizar Galpão: [Descricao do Erro]"
          }
          ```
        """
    db = SessionLocalExemplo()
    editar_galpao = select(Galpao).where(Galpao.id_galpao == int(var_id))
    result_galpao = db.execute(editar_galpao).scalar_one_or_none()
    if request.method == "PUT":
        dados = request.get_json()
        cidade = dados.get("cidade")
        estado = dados.get("estado")
        print(f"{cidade}/{estado}")
        if not cidade or not estado or cidade == "undefined" or estado == "undefined":
            return jsonify({"msg": "Valores Indefinidos","status": "danger"}), 400

        sql_vgalpao = select(Galpao).where(Galpao.cidade == cidade).where(Galpao.estado == estado)
        r_vgalpao = db.execute(sql_vgalpao).first()

        if r_vgalpao:
            return jsonify({"msg": "Galpao já foi editado","status": "danger"}), 409

        try:
            result_galpao.cidade = cidade
            result_galpao.estado = estado
            db.commit()
            return jsonify({"msg": "Galpão atualizado com sucesso","status":"success"}), 200
        except Exception as e:
            db.rollback()
            print(f"ERROR: {e}")
            return jsonify({"msg": f"Erro ao atualizar Galpão: {str(e)}","status":"warning"})
        finally:
            db.close()


if __name__ == "__main__":
    app.run(debug=True, port=5006, host='0.0.0.0')
