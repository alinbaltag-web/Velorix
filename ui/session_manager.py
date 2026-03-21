# session_manager.py
# Sistem centralizat de gestionare a sesiunii utilizatorului

class SessionManager:
    _logged_in = False
    _user_email = None
    _user_role = None
    _login_time = None

    @classmethod
    def login(cls, email, role):
        """Seteaza informatiile sesiunii dupa autentificare."""
        import datetime
        cls._logged_in = True
        cls._user_email = email
        cls._user_role = role
        cls._login_time = datetime.datetime.now()

    @classmethod
    def logout(cls):
        """Reseteaza complet sesiunea."""
        cls._logged_in = False
        cls._user_email = None
        cls._user_role = None
        cls._login_time = None

    @classmethod
    def is_logged_in(cls):
        """Returneaza True daca exista o sesiune activa."""
        return cls._logged_in

    @classmethod
    def get_user(cls):
        """Returneaza emailul utilizatorului logat."""
        return cls._user_email

    @classmethod
    def get_role(cls):
        """Returneaza rolul utilizatorului logat."""
        return cls._user_role

    @classmethod
    def get_login_time(cls):
        """Returneaza ora logarii."""
        return cls._login_time
