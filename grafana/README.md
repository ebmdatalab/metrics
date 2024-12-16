# Grafana deployment instructions
## Create app

```bash
dokku$ dokku apps:create grafana
dokku$ dokku domains:add grafana dashboards.opensafely.org
```

## Create postgresql db for grafana

* on DO db cluster
  * postgresql version to match target server - currently 14 on dokku3

## create persistent storage

```bash
# the grafana container runs as uid 472 (grafana)
# the other dokku containers on dokku3 run as uid 1013 (dokku)
# let's tell the container to run as 1013, then we can use the same file permissions
dokku$ dokku docker-options:add grafana deploy "--user 1013"
dokku$ dokku docker-options:add grafana run "--user 1013"
dokku$ dokku storage:ensure-directory grafana

myuser$ sudo chown -R dokku:dokku /var/lib/dokku/data/storage/grafana

dokku$ dokku storage:mount grafana /var/lib/dokku/data/storage/grafana:/var/lib/grafana
```

## Configure app

```bash
dokku config:set grafana GF_DATABASE_TYPE="postgres"
dokku config:set grafana GF_DATABASE_HOST="xxx:5432"
dokku config:set grafana GF_DATABASE_NAME="grafana"
dokku config:set grafana GF_DATABASE_USER="grafana"
dokku config:set grafana GF_DATABASE_PASSWORD="xxx"
dokku config:set grafana GF_DATABASE_SSL_MODE="require"
dokku config:set grafana GF_SERVER_ROOT_URL="https://dashboards.opensafely.org/"
dokku config:set grafana GF_INSTALL_PLUGINS="grafana-github-datasource"
dokku config:set grafana GF_FEATURE_TOGGLES_ENABLE="publicDashboards"
```

## Letsencrypt

```bash
dokku$ dokku ports:add grafana http:80:3000
# TODO: block access to port 3000?
dokku$ dokku letsencrypt:enable grafana
```

## Create postgresql connection in Grafana

### Configure user on postgresql db cluster

* Create `grafanareader` user on db cluster in DigitalOcean control panel for primary node.
* By default `grafanareader` cannot connect to the `jobserver` database. Connect to primary node with psql and allow connections (via dokku4):

```sh
$ psql -h <primary node hostname> -p<primary node port> -Udoadmin -d defaultdb
```

```sql
GRANT CONNECT ON database jobserver TO grafanareader;
```

* `grafanareader` will still fail with e.g. "db query error: pq: permission denied for table applications_application"
* configure access as required:

```sql
GRANT SELECT ON applications_application, applications_cmoprioritylistpage, applications_commercialinvolvementpage, applications_datasetspage, applications_legalbasispage, applications_previousehrexperiencepage, applications_recordleveldatapage, applications_referencespage, applications_researcherregistration, applications_sharingcodepage, applications_shortdatareportpage, applications_sponsordetailspage, applications_studydatapage, applications_studyfundingpage, applications_studyinformationpage, applications_studypurposepage, applications_teamdetailspage, applications_typeofstudypage, interactive_analysisrequest, jobserver_backend, jobserver_backendmembership, jobserver_job, jobserver_jobrequest, jobserver_org, jobserver_orgmembership, jobserver_project, jobserver_projectcollaboration, jobserver_projectmembership, jobserver_publishrequest, jobserver_release, jobserver_releasefile, jobserver_releasefilereview, jobserver_repo, jobserver_report, jobserver_snapshot, jobserver_snapshot_files, jobserver_stats, jobserver_workspace, redirects_redirect TO grafanareader;

CREATE VIEW jobserver_user_grafana AS SELECT id,last_login,username,date_joined,fullname,created_by_id,login_token_expires_at,pat_expires_at,roles FROM jobserver_user;

GRANT SELECT ON jobserver_user_grafana TO grafanareader;
```

The `jobserver_user_grafana` view may need recreating if the underlying `jobserver_user` table changes.

### Connect from Grafana

Go to the DigitalOcean db cluster read-only node `Connection Details` & get some credentials (`Host`, `Database`, `User`, `Password`). Enter these into a new data source in the Grafana UI by following these links:

* Adminstration
* Plugins
* PostgreSQL
* Add new data source

### Missing datasource

If you import a Dashboard from a JSON file, the visualisations may error with "Could not find datasource $UUID". It is sometimes possible to fix this by some combination of hitting "Run query" & "Refresh", otherwise you could recreate the visulation by copy-pasting SQL etc.

## Auto-update

In order to get auto-updates we use a Dockerfile with a specific SHA of the upstream grafana image, which [dependabot is monitoring](https://github.com/ebmdatalab/metrics/blob/c46ba14c5f5f52ac2232da32542d226acea85be9/.github/dependabot.yml#L15-L18). We have a Github Action to auto-merge dependabot's PRs, and the merge to main should trigger a deployment of the new version of grafana to our instance.
