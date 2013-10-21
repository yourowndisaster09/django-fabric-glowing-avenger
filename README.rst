==========
Deployment
==========
Continuous Integration Server Setup
-----------------------------------
We assume your Amazon instances are ready, security groups are configured,
and keys are downloaded. Place all necessary pem files in local ~/.ssh directory.
Configure the file **fabconf.py** with your project specifics, and run:

>>> fab ci setup_jenkins_server


Secure your Jenkins server
--------------------------

On the jenkins user interface, select `Manage Jenkins` > `Configure Global Security` > Check `Enable security`.

    Under the `Security Realm`, choose `Jenkins’s own user database` and uncheck `Allow users to sign up`.

    Under `Authorization`, select `Matrix-based security`. Give read access to Anonymous, and create your user having all permissions.

    Go to **/signup** and fill the signup form with the username you added.


Add Plugins
-----------

Select `Manage Jenkins` > `Manage Plugins` > `Advanced` tab, and click the `Check Now` button to update downloadable plugins. Under the `Available` tab, install the following:

- Git Client Plugin
- Git Plugin
- Cobertura Plugin
- Violations
- SLOCCount Plugin
- Green Balls

Add your username and email in `Manage Jenkins` > `Configure System` > `Git plugin`


Add test job
------------

Click `New job` > `Free-style software project`. Configure the following:

    Under `Source Code Management`, select `Git`, and enter REPOSITORY_URL your git@host:repo.git

    Under `Build Triggers` > Select `Trigger builds remotely (e.g., from scripts)` and add a RANDOM_TOKEN. Note that you must add this token to your project's bitbucket hooks. To configure the hook, get your user's API token from `People` > USERNAME > `Configure` > `API Token` > `Show`. Add a hook with the following parameters:

        Endpoint = http://USERNAME:API_TOKEN@JENKINS_URL

        Project name = JOBNAME

        Token = RANDOM_TOKEN

    Under `Build` > Select `Execute Shell`, and input:

        >>> bash $WORKSPACE/tools/jenkins/ci.sh`

    Under `Post-build Actions`:
        1. `Build other projects` > Input the name of your development job
        2. `Publish Cobertura Coverage Report` > PROJECT/reports/coverage.xml
        3. `Publish Junit test result Report` > PROJECT/reports/junit.xml
        4. `Publish SLOCCount analysis results` > PROJECT/reports/sloccount.report
        5. `Report Violations`
            a. `csslint` > PROJECT/reports/csslint.report
            b. `jslint` > PROJECT/reports/jshint.xml
            c. `pep8` > PROJECT/reports/pep8.report
            d. `pylint` > PROJECT/reports/pyflakes.report, PROJECT/reports/pylint.report


Add environment jobs
--------------------

Install ubuntu packages and dependencies for your environment server:

>>> fab <env=development|staging|production> install_dependencies

Add a deployment key for git

>>> fab <env=development|staging|production> add_pub_key

Note that you must create a secret file containing env variables of django secret keys and upload it to your remote server

>>> fab <env=development|staging|production> upload_secrets:<local_path>

An example of your secret file:
::

    #!/bin/bash

    export DJANGO_SETTINGS_MODULE=<project>.settings.<env=development|staging|production>
    export EMAIL_HOST=''
    export EMAIL_HOST_PASSWORD=''
    export EMAIL_HOST_USER=''
    export EMAIL_PORT=
    export DATABASE_NAME=''
    export DATABASE_USER=''
    export DATABASE_PASSWORD=''
    export SECRET_KEY=''

Setup a Postgresql database from your secret file configuration

>>> fab <env=development|staging|production> setup_database_from_secrets

Add jobs for other envs by clicking `New job` > `Free-style software project`. Configure the following:

    Under `Source Code Management`, select `Git`, and enter REPOSITORY_URL your git@host:repo.git

    Under `Build` > Select `Execute Shell`, and input:

        >>> bash $WORKSPACE/tools/jenkins/<env=development|staging|production>.sh
