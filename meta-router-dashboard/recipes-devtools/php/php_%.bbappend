# The dashboard only needs PHP core/CGI. Avoid pulling database and TLS clients
# into this small firmware image through php's upstream default PACKAGECONFIG.
PACKAGECONFIG:pn-php = ""
