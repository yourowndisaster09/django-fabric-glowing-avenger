# Django + nginx + git + postgresql + memcached + supervisor

import datetime, time
from os.path import dirname, join
from sys import path

from fabric.api import env, settings
from fabric.context_managers import cd, hide, prefix
from fabric.contrib import django
from fabric.contrib.console import confirm
from fabric.contrib.files import contains, exists, sed
from fabric.operations import get, local, put, run, sudo
from fabric.utils import warn

import fabconf

path.append(dirname(__file__))


##############################
## Access to remote servers ##
##############################

def ci():
    """
    Access ci server locally

    """
    env.key_filename = join('~/.ssh', fabconf.CI_KEY_FILENAME)
    env.host_string = fabconf.CI_HOST
    env.env_name = 'ci'

def _initialize_variables():
    env.project = fabconf.PROJECT
    env.virtualenv = fabconf.VIRTUALENV
    env.repository = fabconf.REPOSITORY

    # Local directories
    env.ssh_dir = '~/.ssh'

    # Remote directories
    env.home = '/home/ubuntu'

    env.project_root = join(env.home, env.project)
    env.django_root = join(env.project_root, env.project)
    env.virtualenv_dir = join(env.home, '.virtualenvs', env.virtualenv)

    if fabconf.USE_SOLR:
        env.solr_root = join(env.home, 'solr')

def development():
    """
    Access development server locally

    """
    env.key_filename = join('~/.ssh', fabconf.DEVELOPMENT_KEY_FILENAME)
    env.host_string = fabconf.DEVELOPMENT_HOST
    env.env_name = 'development'
    _initialize_variables()

def staging():
    """
    Access staging server locally

    """
    env.key_filename = join('~/.ssh', fabconf.STAGING_KEY_FILENAME)
    env.host_string = fabconf.STAGING_HOST
    env.env_name = 'staging'
    _initialize_variables()

def production():
    """
    Access production server locally

    """
    env.key_filename = join('~/.ssh', fabconf.PRODUCTION_KEY_FILENAME)
    env.host_string = fabconf.PRODUCTION_HOST
    env.env_name = 'production'
    _initialize_variables()

def test_connect():
    run('echo OK')


##################################
## Ubuntu packages installation ##
##################################

def install(installs_str):
    sudo('apt-get -y install %s' % installs_str)

def install_jenkins():
    run('wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -')
    sudo('sh -c "echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list"')
    sudo('apt-get -y update')
    sudo('apt-get -y install jenkins')

def install_git():
    sudo('apt-get -y install git')

def install_nginx():
    sudo('apt-get -y update')
    sudo('apt-get -y install nginx')

def install_postgres():
    sudo('apt-get -y install python-setuptools libpq-dev python-dev')
    sudo('apt-get -y install postgresql-9.1 python-psycopg2')

def install_memcached():
    sudo('apt-get -y install memcached')

def install_supervisor():
    sudo('apt-get -y install supervisor')

def install_virtualenvwrapper():
    sudo('apt-get install -y python-pip')
    sudo('pip install virtualenvwrapper')

def install_npm():
    sudo('add-apt-repository ppa:richarvey/nodejs')
    sudo('apt-get -y update')
    sudo('apt-get install -y nodejs npm')

def install_yuglify():
    sudo('npm install yuglify -g')

def install_less():
    sudo('npm install less -g')

def install_jshint():
    sudo('npm install jshint -g')

def install_csslint():
    sudo('npm install csslint -g')

def install_sloccount():
    sudo('apt-get install -y sloccount')

def install_pil():
    pil = ['libjpeg8-dev', 'zlib1g-dev', 'libfreetype6-dev', 'liblcms1-dev']
    pil_links = ['libjpeg.so', 'libz.so', 'libfreetype.so', 'liblcms.so']
    sudo('apt-get install -y %s' % ' '.join(pil))
    with settings(warn_only=True):
        for link in pil_links:
            if run('test -h /usr/lib/%s' % link).failed:
                sudo('ln -s /usr/lib/x86_64-linux-gnu/%s /usr/lib' % link)

def install_solr(replace=False):
    if replace or not exists('/var/lib/solr'):
        run('wget -c http://archive.apache.org/dist/lucene/solr/4.5.1/solr-4.5.1.tgz')
        run('tar xzf solr-4.5.1.tgz')
        run('mv solr-4.5.1/example /home/ubuntu/solr')
        run('rm -rf solr-4.5.1.tgz')
        run('rm -rf solr-4.5.1')

def install_rabbitmq():
    sudo('apt-get install -y rabbitmq-server')

def install_additional_packages():
    if fabconf.ADDITIONAL_PACKAGES:
        install(" ".join(fabconf.ADDITIONAL_PACKAGES))


######################
## Service commands ##
######################

def nginx(cmd):
    sudo('service nginx %s' % cmd)

def postgresql(cmd):
    sudo('service postgresql %s' % cmd)

def memcached(cmd):
    sudo('service memcached %s' % cmd, pty=False)

def supervisor(cmd):
    sudo('service supervisor %s' % cmd)

def rabbitmq(cmd):
    sudo('service rabbitmq-server %s' % cmd)

def supervisorctl(cmd):
    sudo('supervisorctl %s' % cmd)

def managepy(cmd):
    with prefix('source %(virtualenv_dir)s/bin/activate' % env):
        with cd(env.django_root):
            with prefix('source ~/.secrets'):
                run('python manage.py %s' % cmd)


###############
## View logs ##
###############
NGINX_ACCESS_LOG = lambda: '/var/log/nginx/%(project)s.access.log;' % env
NGINX_ERROR_LOG = lambda: '/var/log/nginx/%(project)s.error.log' % env
MEMCACHED_LOG = lambda: '/var/log/memcached.log'
GUNICORN_LOG = lambda: '/var/log/%(project)s/gunicorn.log' % env
GUNICORN_ERROR_LOG = lambda: '/var/log/%(project)s/gunicorn.err' % env
SOLR_LOG = lambda: '/var/log/%(project)s/solr.log' % env
SOLR_ERROR_LOG = lambda: '/var/log/%(project)s/solr.err' % env
CELERY_LOG = lambda: '/var/log/%(project)s/celery.log' % env
CELERY_ERROR_LOG = lambda: '/var/log/%(project)s/celery.err' % env

def tail(logfile):
    if logfile in globals():
        logfile = globals()[logfile]()
    run('tail -f %s' % logfile)

def tac(logfile):
    if logfile in globals():
        logfile = globals()[logfile]()
    run('tac %s | less' % logfile)

def cat(logfile):
    if logfile in globals():
        logfile = globals()[logfile]()
    run('cat %s | less' % logfile)


##############################
## Postgres database setups ##
##############################
def setup_database(name, user, password):
    """
    Creates a postgres database

    """
    with settings(warn_only=True):
        sudo('psql -c "CREATE ROLE {0} WITH PASSWORD \'{1}\' NOSUPERUSER CREATEDB NOCREATEROLE LOGIN;"'.format(user, password), user='postgres')
        sudo('psql -c "CREATE DATABASE {0} WITH OWNER={1} TEMPLATE=template0 ENCODING=\'utf-8\';"'.format(name, user), user='postgres')

    pg_hba_location = '/etc/postgresql/9.1/main/pg_hba.conf'
    if contains(pg_hba_location, 'peer', use_sudo=True):
        sed(pg_hba_location, 'peer', 'trust', use_sudo=True)
        postgresql('restart')

def setup_database_from_secrets():
    """
    Gets database configurations from environment variables set in secrets

    """
    with settings(hide('everything')):
        with prefix('source ~/.secrets'):
            name = run('echo $DATABASE_NAME')
            user = run('echo $DATABASE_USER')
            password = run('echo $DATABASE_PASSWORD')
    setup_database(name, user, password)

def setup_database_from_settings():
    """
    Gets database configurations from local django settings file

    """
    from django.conf import settings as djangosettings
    database = djangosettings.DATABASES.get('default')
    name = database.get('NAME')
    user = database.get('USER')
    password = database.get('PASSWORD')
    setup_database(name, user, password)

def download_database(local_path=None):
    with settings(hide('everything')):
        with prefix('source ~/.secrets'):
            dbname = run('echo $DATABASE_NAME')
    now = datetime.datetime.utcnow().strftime("%m-%d-%y-%H-%M-%S")
    filename = '/tmp/{0}-{1}.sql'.format(dbname, now)
    sudo('pg_dump {0} > {1}'.format(dbname, filename), user='postgres')
    get(filename, local_path)
    sudo('mv %s /var/backups' % filename)


############################
## RabbitMQ Broker setups ##
############################

def setup_broker(user, password, vhost):
    """
    Creates a RabbitMQ user, a virtual host
    and allow that user access to that virtual host

    """
    with settings(warn_only=True):
        sudo('rabbitmqctl add_user {0} {1}'.format(user, password))
        sudo('rabbitmqctl add_vhost {0}'.format(vhost))
        sudo('rabbitmqctl set_permissions -p {0} {1} ".*" ".*" ".*"'.format(vhost, user))
    rabbitmq('restart')

def setup_broker_from_secrets():
    """
    Gets broker configurations from environment variables set in secrets

    """
    with settings(hide('everything')):
        with prefix('source ~/.secrets'):
            user = run('echo $BROKER_USER')
            password = run('echo $BROKER_PASSWORD')
            vhost = run('echo $BROKER_VHOST')
    setup_broker(user, password, vhost)


#####################################
## Remote environment server utils ##
#####################################

def upload_secrets(secret_file):
    """
    Upload secret file to remote server

    """
    put(secret_file, '~/.secrets')

def _add_pub_key(location, user):
    pubkey_exists = False
    if exists(location, use_sudo=True):
        pubkey_exists = True
        if confirm('Pub key already exists. Overwrite?'):
            pubkey_exists = False
    if not pubkey_exists:
        if user:
            sudo('ssh-keygen', user=user)
        else:
            run('ssh-keygen')
    if user:
        sudo('cat %s' % location, user=user)
    else:
        run('cat %s' % location)
    if confirm('Update as deployment key? Make sure you added the public key as deployment key on bitbucket...'):
        if user:
            sudo('git ls-remote -h %s HEAD' % fabconf.REPOSITORY, user=user)
        else:
            run('git ls-remote -h %s HEAD' % fabconf.REPOSITORY)

def add_pub_key():
    """
    Generate pub key as git deployment key

    """
    location = '/home/ubuntu/.ssh/id_rsa.pub'
    user = None
    _add_pub_key(location, user)

def create_superuser():
    managepy('createsuperuser')

def install_dependencies():
    install_git()
    install_nginx()
    install_virtualenvwrapper()
    install_postgres()
    install_memcached()
    install_supervisor()
    install_npm()
    install_yuglify()
    install_less()

    if fabconf.USE_SOLR:
        install_solr()

    if fabconf.USE_PIL:
        install_pil()

    if fabconf.CELERY:
        install_rabbitmq()

def create_virtualenv():
    with settings(warn_only=True):
        if not exists(env.virtualenv_dir):
            with prefix('source /usr/local/bin/virtualenvwrapper.sh'):
                run('mkvirtualenv --no-site-packages --distribute %(virtualenv)s' % env)

def pip_install(pkg):
    with cd(env.project_root):
        with prefix('source %(virtualenv_dir)s/bin/activate' % env):
            run('pip install %s' % pkg)

def pip_uninstall(pkg):
    with cd(env.project_root):
        with prefix('source %(virtualenv_dir)s/bin/activate' % env):
            run('pip uninstall %s' % pkg)

def install_django_packages():
    pip_install('-r requirements/%(env_name)s.txt' % env)

def get_project_from_repo():
    if not exists(env.project_root):
        run('git clone %(repository)s' % env)
    else:
        with cd(env.project_root):
            if env.env_name == 'development':
                with settings(warn_only=True):
                    run('git checkout -b development')
                    run('git pull origin development')
            elif env.env_name == 'staging':
                with settings(warn_only=True):
                    run('git checkout -b staging')
                    run('git pull origin staging')
            elif env.env_name == 'production':
                run('git pull')

def prepare_django_project():
    managepy('syncdb --noinput')
    managepy('migrate --noinput')
    managepy('collectstatic --noinput')

    for cmd in fabconf.ADDITIONAL_MANAGEMENT_COMMANDS:
        managepy(cmd)

def prepare_solr():
    with cd(env.project_root):
        run('cp tools/solr/solrconfig.xml ~/solr/solr/collection1/conf/solrconfig.xml')
        run('cp tools/solr/stopwords_en.txt ~/solr/solr/collection1/conf/stopwords_en.txt')
    managepy('build_solr_schema > ~/solr/solr/collection1/conf/schema.xml')

def rebuild_solr():
    managepy('rebuild_index --noinput')

def access_shell():
    managepy('shell --plain')

def prepare_log_directory():
    sudo('mkdir -p /var/log/%(project)s' % env)

def setup_env_supervisor():
    supervisor('stop')
    with cd(env.project_root):
        sudo('cp tools/supervisor/%(env_name)s.conf /etc/supervisor/conf.d/%(project)s.conf' % env)
    if fabconf.USE_SOLR:
        prepare_solr()
    supervisor('start')
    if fabconf.USE_SOLR:
        time.sleep(10)
        rebuild_solr()

def setup_env_memcache():
    with cd(env.project_root):
        sudo('cp tools/memcached/%(env_name)s.conf /etc/memcached.conf' % env)
    memcached('restart')

def setup_env_nginx():
    with cd(env.project_root):
        sudo('cp tools/nginx/%(env_name)s /etc/nginx/sites-available/%(project)s' % env)
    sudo('ln -sf /etc/nginx/sites-available/%(project)s /etc/nginx/sites-enabled/' % env)
    nginx('restart')

def deploy():
    """
    Deploy an environment.

    """
    install_additional_packages()
    get_project_from_repo()

    create_virtualenv()
    install_django_packages()
    prepare_django_project()

    prepare_log_directory()

    setup_env_supervisor()
    setup_env_memcache()
    setup_env_nginx()


####################################
## Jenkins server setup specifics ##
####################################

def add_pub_key_as_jenkins():
    """
    Generate pub key on user jenkins as git deployment key

    """
    location = '/var/lib/jenkins/.ssh/id_rsa.pub'
    user = 'jenkins'
    _add_pub_key(location, user)

def upload_ci_nginx_settings():
    put('tools/nginx/ci', '/etc/nginx/sites-available/jenkins', use_sudo=True)
    sudo('ln -sf /etc/nginx/sites-available/jenkins /etc/nginx/sites-enabled/')

def upload_env_keys():
    """
    Uploads environment keys to ssh folder in ci server

    """
    with settings(warn_only=True):
        dev_key = join('~/.ssh', fabconf.DEVELOPMENT_KEY_FILENAME)
        if local('cat %s' % dev_key).failed:
            warn('Place your development public key in ssh folder')
        else:
            put(dev_key, '/var/lib/jenkins/.ssh', use_sudo=True)
            sudo('ssh -o "StrictHostKeyChecking no" %s' % fabconf.DEVELOPMENT_HOST, user='jenkins')

        staging_key = join('~/.ssh', fabconf.STAGING_KEY_FILENAME)
        if local('cat %s' % staging_key).failed:
            warn('Place your staging public key in ssh folder')
        else:
            put(staging_key, '/var/lib/jenkins/.ssh', use_sudo=True)
            sudo('ssh -o "StrictHostKeyChecking no" %s' % fabconf.STAGING_HOST, user='jenkins')

        production_key = join('~/.ssh', fabconf.PRODUCTION_KEY_FILENAME)
        if local('cat %s' % production_key).failed:
            warn('Place your production public key in ssh folder')
        else:
            put(production_key, '/var/lib/jenkins/.ssh', use_sudo=True)
            sudo('ssh -o "StrictHostKeyChecking no" %s' % fabconf.PRODUCTION_HOST, user='jenkins')

def setup_jenkins_server():
    """
    Complete setup for the ci server

    """
    install_jenkins()
    install_git()
    install_nginx()
    install_virtualenvwrapper()
    install_postgres()

    install_npm()
    install_jshint()
    install_csslint()
    install_sloccount()
    install('ttf-dejavu')

    install_additional_packages()

    upload_ci_nginx_settings()
    django.settings_module(fabconf.CI_SETTINGS_PATH)
    setup_database_from_settings()
    add_pub_key_as_jenkins()
    upload_env_keys()
    nginx('restart')
