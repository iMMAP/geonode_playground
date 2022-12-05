# ASDC (Afghanistan Spatial Data Center)

GeoNode template project. Generates a django project with GeoNode support.

## Prerequisites

- Java OpenJDK
- Python 3.8 , virtualenvwrapper and virtualenv
- pip
- Node v 14

## Installation

### 1 - Create virtual environment

```bash
mkvirtualenv my_geonode
```

```bash
workon my_geonode
```

### 2 - Clone the geonode-project repo from Github

```bash
git clone https://github.com/iMMAP/geonode_playground.git -b master

cd geonode_playground/src
```

3 - Install Django framework

```bash
pip install Django==3.2.13
```

### 4 - Install requirements

Install all the requirements for the GeoNode-Project and install the GeoNode-Project using pip

```bash
pip install -r requirements.txt --upgrade

pip install -e . --upgrade

```

### 5 - Install GDAL Utilities for Python

```bash
pip install pygdal=="`gdal-config --version`.*"  # or refer to the link <Install GDAL for Development <https://training.geonode.geo-solutions.it/005_dev_workshop/004_devel_env/gdal_install.html>
```

### 6 - Install and Configure the PostgreSQL Database System

```bash
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg main" >> /etc/apt/sources.list.d/pgdg.list'
sudo wget --no-check-certificate --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update -y; sudo apt install -y postgresql-13 postgresql-13-postgis-3 postgresql-13-postgis-3-scripts postgresql-13 postgresql-client-13
```

### 7 - Databases and Permissions

Create geonode user

```bash
sudo service postgresql start
sudo -u postgres createuser -P my_geonode

# Use the password: geonode
```

Create my_geonode and my_geonode_data with owner my_geonode

```bash
sudo -u postgres createdb -O my_geonode my_geonode
sudo -u postgres createdb -O my_geonode my_geonode_data
```

create PostGIS extensions

```bash
sudo -u postgres psql -d my_geonode -c 'CREATE EXTENSION postgis;'
sudo -u postgres psql -d my_geonode -c 'GRANT ALL ON geometry_columns TO PUBLIC;'
sudo -u postgres psql -d my_geonode -c 'GRANT ALL ON spatial_ref_sys TO PUBLIC;'
sudo -u postgres psql -d my_geonode -c 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO my_geonode;'

sudo -u postgres psql -d my_geonode_data -c 'CREATE EXTENSION postgis;'
sudo -u postgres psql -d my_geonode_data -c 'GRANT ALL ON geometry_columns TO PUBLIC;'
sudo -u postgres psql -d my_geonode_data -c 'GRANT ALL ON spatial_ref_sys TO PUBLIC;'
sudo -u postgres psql -d my_geonode_data -c 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO my_geonode;'
```

change user access policies for local connections in the file `pg_hba.conf`

```bash
sudo nano /etc/postgresql/13/main/pg_hba.conf
```

Scroll down to the bottom of the document. We want to make local connection `trusted` for the default user.

Make sure your configuration looks like the one below.

```bash
...
# DO NOT DISABLE!
# If you change this first entry you will need to make sure that the
# database superuser can access the database using some other method.
# Noninteractive access to all databases is required during automatic
# maintenance (custom daily cronjobs, replication, and similar tasks).
#
# Database administrative login by Unix domain socket
local   all             postgres                                trust

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     md5
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
# Allow replication connections from localhost, by a user with the
# replication privilege.
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5
```

Restart PostgreSQL to make the change effective.

```bash
sudo service postgresql restart
```

### 8 - Install GeoServer, Tomcat and run database migrations using paver

```bash
# Inside the src folder

sh ./paver_dev.sh setup

sh ./paver_dev.sh sync

```

### 9 - Start the project

```bash
# Inside the src folder

sh ./paver_dev.sh start
```
