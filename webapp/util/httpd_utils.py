from subprocess import Popen, PIPE

HTTPD_PASSWD_FILE = '/etc/httpd/.htpasswd'

def add_httpd_user(username:str, password:str):
    """ Add a new user + password to the httpd password file """
    httpd_call = Popen(['htpasswd', '-i', HTTPD_PASSWD_FILE, username], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = httpd_call.communicate(input=password.encode())

    if httpd_call.returncode:
        raise RuntimeError(f"htpasswd returned nonzero exit code: {httpd_call.returncode}: {err}")