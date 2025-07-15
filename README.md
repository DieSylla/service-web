Projet d'Architecture Logicielle - Services Web
Prérequis

Python 3.8 ou supérieur
SQLite
Dépendances : pip install -r requirements.txt

Initialisation de la base de données

Exécutez le script pour créer la base SQLite et insérer des données de test :python init_db.py


Vérifiez les données :python check_db.py



Lancer le service SOAP

Exécutez :python soap_service.py


Accédez au WSDL : http://localhost:8000/?wsdl
Testez avec SoapUI ou un client Python (par exemple, avec zeep).

Lancer le service REST

Exécutez :python rest_service.py


Testez les endpoints avec Postman ou un navigateur :
Liste des articles : http://localhost:5000/articles?format=json
Articles par catégorie : http://localhost:5000/articles/by-category?format=xml
Articles d’une catégorie : http://localhost:5000/articles/category/1?format=json



Données de test

Utilisateur admin : admin1 / password123
Jeton valide : token12345
Catégories : Technologie (ID 1), Sport (ID 2), Culture (ID 3)

Notes

Les mots de passe sont hachés avec bcrypt pour plus de sécurité.
Coordonnez-vous avec l’équipe pour intégrer les services avec le site web et l’application client.
