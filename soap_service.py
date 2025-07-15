from flask import Flask, request, make_response
from lxml import etree
import sqlite3
import bcrypt
import logging
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurer les journaux
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Connexion à la base de données SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Vérification du jeton
def verify_token(token, require_admin=False):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT t.*, u.role FROM tokens t JOIN users u ON t.user_id = u.id WHERE t.token = ? AND t.expires_at > datetime('now')", (token,))
        result = cursor.fetchone()
        conn.close()
        if result is None:
            logger.error("Jeton invalide ou expiré")
            return None
        if require_admin and result['role'] != 'admin':
            logger.error("Opération réservée aux administrateurs")
            return None
        return result
    except sqlite3.Error as e:
        logger.error(f"Erreur lors de la vérification du jeton: {e}")
        return None

# Générer une réponse SOAP
def create_soap_response(operation, content):
    envelope = etree.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
    body = etree.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
    response = etree.SubElement(body, f"{{http://example.com/userservice}}{operation}Response")
    response.append(content)
    return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

# Générer une erreur SOAP
def create_soap_fault(message):
    envelope = etree.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
    body = etree.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
    fault = etree.SubElement(body, "{http://schemas.xmlsoap.org/soap/envelope/}Fault")
    etree.SubElement(fault, "faultcode").text = "soap:Server"
    etree.SubElement(fault, "faultstring").text = message
    return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

@app.route('/userService', methods=['POST'])
def user_service():
    try:
        # Parse la requête SOAP
        request_data = request.get_data()
        root = etree.fromstring(request_data)
        ns = {'use': 'http://example.com/userservice'}
        operation = root.find('.//use:*', namespaces=ns)
        if operation is None:
            logger.error("Aucune opération SOAP trouvée dans la requête")
            return make_response(create_soap_fault("Opération inconnue"), 400, {'Content-Type': 'text/xml'})
        operation = operation.tag.split('}')[-1]

        if operation == 'generateToken':
            login_elem = root.find('.//use:login', ns)
            password_elem = root.find('.//use:password', ns)
            duration_elem = root.find('.//use:duration_hours', ns)

            if login_elem is None or password_elem is None or duration_elem is None:
                logger.error("Un ou plusieurs éléments XML manquants (login, password, duration_hours)")
                return make_response(create_soap_fault("Requête XML invalide: éléments manquants"), 400, {'Content-Type': 'text/xml'})
            
            login = login_elem.text
            password = password_elem.text
            duration_hours = duration_elem.text
            
            if not login or not password or not duration_hours:
                logger.error("Un ou plusieurs champs XML sont vides")
                return make_response(create_soap_fault("Requête XML invalide: champs vides"), 400, {'Content-Type': 'text/xml'})
            
            try:
                duration_hours = int(duration_hours)
            except ValueError:
                logger.error("duration_hours n'est pas un entier valide")
                return make_response(create_soap_fault("duration_hours doit être un entier"), 400, {'Content-Type': 'text/xml'})

            logger.debug(f"Génération de jeton demandée pour login={login}")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE login = ?", (login,))
            user = cursor.fetchone()
            if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                conn.close()
                logger.error("Échec de l'authentification pour génération de jeton")
                return make_response(create_soap_fault("Identifiants invalides"), 401, {'Content-Type': 'text/xml'})
            if user['role'] != 'admin':
                conn.close()
                logger.error("Génération de jeton réservée aux administrateurs")
                return make_response(create_soap_fault("Opération réservée aux administrateurs"), 403, {'Content-Type': 'text/xml'})
            token = str(uuid.uuid4())
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(hours=duration_hours)
            cursor.execute("INSERT INTO tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                           (token, user['id'], created_at, expires_at))
            conn.commit()
            conn.close()
            logger.info(f"Jeton généré: {token} pour user_id={user['id']}")
            result = etree.Element("token")
            result.text = token
            return make_response(create_soap_response('generateToken', result), 200, {'Content-Type': 'text/xml'})
        
        elif operation == 'authenticateUser':
            login_elem = root.find('.//use:login', ns)
            password_elem = root.find('.//use:password', ns)
            token_elem = root.find('.//use:token', ns)

            if login_elem is None or password_elem is None or token_elem is None:
                logger.error("Un ou plusieurs éléments XML manquants (login, password, token)")
                return make_response(create_soap_fault("Requête XML invalide: éléments manquants"), 400, {'Content-Type': 'text/xml'})

            login = login_elem.text
            password = password_elem.text
            token = token_elem.text

            logger.debug(f"Authentification demandée pour login={login}, token={token}")
            if not verify_token(token):
                return make_response(create_soap_fault("Jeton invalide"), 401, {'Content-Type': 'text/xml'})
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE login = ?", (login,))
            user = cursor.fetchone()
            conn.close()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                logger.info(f"Authentification réussie pour {login}")
                result = etree.Element("isAdmin")
                result.text = "true" if user['role'] == 'admin' else "false"
                return make_response(create_soap_response('authenticateUser', result), 200, {'Content-Type': 'text/xml'})
            
            logger.error("Échec de l'authentification")
            return make_response(create_soap_fault("Identifiants invalides"), 401, {'Content-Type': 'text/xml'})

        elif operation == 'listUsers':
            token = root.find('.//use:token', ns).text
            logger.debug(f"Liste des utilisateurs demandée, token={token}")
            if not verify_token(token):
                return make_response(create_soap_fault("Jeton invalide"), 401, {'Content-Type': 'text/xml'})
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, login, role FROM users")
            users = cursor.fetchall()
            conn.close()
            users_elem = etree.Element("users")
            for user in users:
                user_elem = etree.SubElement(users_elem, "user")
                etree.SubElement(user_elem, "id").text = str(user['id'])
                etree.SubElement(user_elem, "login").text = user['login']
                etree.SubElement(user_elem, "role").text = user['role']
            logger.info(f"{len(users)} utilisateurs retournés")
            return make_response(create_soap_response('listUsers', users_elem), 200, {'Content-Type': 'text/xml'})

        elif operation == 'addUser':
            token = root.find('.//use:token', ns).text
            login = root.find('.//use:login', ns).text
            password = root.find('.//use:password', ns).text
            role = root.find('.//use:role', ns).text
            logger.debug(f"Ajout d'utilisateur: login={login}, role={role}, token={token}")
            if not verify_token(token, require_admin=True):
                return make_response(create_soap_fault("Jeton invalide ou droits insuffisants"), 403, {'Content-Type': 'text/xml'})
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (login, password, role) VALUES (?, ?, ?)", (login, hashed_password, role))
                conn.commit()
                logger.info(f"Utilisateur {login} ajouté")
                result = etree.Element("success")
                result.text = "true"
                return make_response(create_soap_response('addUser', result), 200, {'Content-Type': 'text/xml'})
            except sqlite3.IntegrityError:
                logger.error("Erreur: Login déjà utilisé")
                return make_response(create_soap_fault("Login déjà utilisé"), 400, {'Content-Type': 'text/xml'})
            finally:
                conn.close()

        elif operation == 'updateUser':
            token = root.find('.//use:token', ns).text
            user_id = root.find('.//use:user_id', ns).text
            login = root.find('.//use:login', ns).text
            password = root.find('.//use:password', ns).text
            role = root.find('.//use:role', ns).text
            logger.debug(f"Mise à jour de l'utilisateur ID={user_id}, token={token}")
            if not verify_token(token, require_admin=True):
                return make_response(create_soap_fault("Jeton invalide ou droits insuffisants"), 403, {'Content-Type': 'text/xml'})
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE users SET login = ?, password = ?, role = ? WHERE id = ?", 
                               (login, hashed_password, role, int(user_id)))
                conn.commit()
                result = etree.Element("success")
                result.text = "true" if cursor.rowcount > 0 else "false"
                logger.info(f"Utilisateur ID={user_id} mis à jour: {result.text}")
                return make_response(create_soap_response('updateUser', result), 200, {'Content-Type': 'text/xml'})
            except sqlite3.IntegrityError:
                logger.error("Erreur: Login déjà utilisé")
                return make_response(create_soap_fault("Login déjà utilisé"), 400, {'Content-Type': 'text/xml'})
            finally:
                conn.close()

        elif operation == 'deleteUser':
            token = root.find('.//use:token', ns).text
            user_id = root.find('.//use:user_id', ns).text
            logger.debug(f"Suppression de l'utilisateur ID={user_id}, token={token}")
            if not verify_token(token, require_admin=True):
                return make_response(create_soap_fault("Jeton invalide ou droits insuffisants"), 403, {'Content-Type': 'text/xml'})
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
            conn.commit()
            result = etree.Element("success")
            result.text = "true" if cursor.rowcount > 0 else "false"
            logger.info(f"Utilisateur ID={user_id} supprimé: {result.text}")
            conn.close()
            return make_response(create_soap_response('deleteUser', result), 200, {'Content-Type': 'text/xml'})

        else:
            return make_response(create_soap_fault("Opération inconnue"), 400, {'Content-Type': 'text/xml'})

    except Exception as e:
        logger.error(f"Erreur lors du traitement de la requête: {e}")
        return make_response(create_soap_fault(str(e)), 500, {'Content-Type': 'text/xml'})

@app.route('/userService/wsdl', methods=['GET'])
def get_wsdl():
    with open('userService.wsdl', 'r') as f:
        wsdl_content = f.read()
    return make_response(wsdl_content, 200, {'Content-Type': 'text/xml'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)