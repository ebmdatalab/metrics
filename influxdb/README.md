# Influxdb deployment instructions
## Create app

```bash
dokku$ dokku apps:create influxdb
# only listen locally
# if devs wish to access the UI externally, they should use an SSH tunnel (see later)
dokku nginx:set node-js-app bind-address-ipv4 127.0.0.1
dokku nginx:set node-js-app bind-address-ipv6 ::1
dokku$ dokku git:set influxdb deploy-branch main
dokku$ dokku builder-dockerfile:set influxdb dockerfile-path influxdb/Dockerfile
```

## create persistent storage


```bash
dokku$ dokku storage:ensure-directory influxdb
dokku storage:mount influxdb /var/lib/dokku/data/storage/influxdb:/var/lib/influxdb
```

## Configure app

```bash
# TODO: not sure what's needed here yet
dokku config:set influxdb MYVAR="myval"
```

## Manually pushing

* set up key on target server
  * madwort adding his regular key for now - needs a better setup

```bash
local$ git clone git@github.com:ebmdatalab/metrics.git
local$ cd sysadmin
local$ git remote add dokku dokku@MYSERVER:influxdb
local$ git push dokku main
```

## Letsencrypt

TODO: not possible to use LE right now because we're not world-accessible :/

```bash
dokku$ dokku ports:add influxdb http:80:3000
# TODO: block access to port 3000?
dokku$ dokku letsencrypt:enable grafana
```

## connection from Grafana

API key?

## See also

https://github.com/thomasfedb/influxdb-dokku

