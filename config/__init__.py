"""
Package initialization for config.
Installs PyMySQL as MySQLdb if available, ensuring seamless MySQL compatibility
on Windows without requiring MSVC C++ compilation tools.
"""
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except (ImportError, AttributeError):
    pass
