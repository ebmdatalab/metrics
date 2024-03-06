from metrics.github import query


def tech_repos(client, org):
    return [r for r in query.repos(client, org) if _is_tech_owned(r)]


def get_repo_ownership(client, orgs):
    repo_owners = []

    for org in orgs:
        ownership = {}
        for team in _TECH_TEAMS:
            for repo in query.team_repos(client, org, team):
                ownership[repo] = team

        active_repos = [
            repo for repo in query.repos(client, org) if not repo.is_archived()
        ]

        for repo in active_repos:
            if repo.name in ownership:
                team = ownership[repo.name]
            else:
                team = None
            repo_owners.append({"organisation": org, "repo": repo.name, "owner": team})

    return repo_owners


def _is_tech_owned(repo):
    # For now we are using a hard-coded list here because we don't have teams set up with repo
    # lists for ebmdatalab. Later we can use the dynamically calculated repo ownership and get
    # rid of this list.
    #
    # We use a deny-list rather than an allow-list so that newly created repos are treated as
    # Tech-owned by default, in the hopes of minimizing surprise.
    return not (repo.org in _NON_TECH_REPOS and repo.name in _NON_TECH_REPOS[repo.org])


# GitHub slugs for the teams we're interested in
_TECH_TEAMS = ["team-rap", "team-rex"]


_NON_TECH_REPOS = {
    "ebmdatalab": [
        "bennett-presentations",
        "bnf-code-to-dmd",
        "change_detection",
        "copiloting",
        "clinicaltrials-act-converter",
        "clinicaltrials-act-tracker",
        "copiloting-publication",
        "datalab-jupyter",
        "dmd-hosp-only",
        "euctr-tracker-code",
        "funding-applications",
        "funding-report",
        "ghost_branded_generics_paper",
        "global-trial-landscape",
        "imagemagick-magick",
        "improvement_radar_prototype",
        "jupyter-notebooks",
        "kurtosis-pericyazine",
        "lidocaine-eng-ire",
        "low-priority-CCG-visit-RCT",
        "nsaid-covid-codelist-notebook",
        "opencorona-sandpit-for-fizz",
        "opensafely-output-review",
        "open-nhs-hospital-use-data",
        "opioids-change-detection-notebook",
        "outliers",
        "prescribing-queries",
        "price-concessions-accuracy-notebook",
        "priceshocks",
        "propaganda",
        "publications",
        "publications-copiloted",
        "retracted.net",
        "retractobot",
        "retractobot-archive",
        "rx-cost-item-analysis",
        "Rx-Quantity-for-Long-Term-Conditions",
        "Rx-Quantity-for-LTCs-notebook",
        "scmd-narcolepsy",
        "seb-test-notebook",
        "service-analytics-team",
        "teaching_resource",
        "trialstracker",
        "vaccinations-covid-codelist-notebook",
        "nimodipine-rct",
        "covid_trials_tracker-covid",
        "datalabsupport",
        "fdaaa_trends",
        "openpathology-web",
        "antibiotics-rct-analysis",
        "seb-docker-test",
        "openprescribing-doacs-workbook",
        "sps-injectable-medicines-notebook",
        "html-template-demo",
        "covid-prescribing-impact-notebook",
        "antibiotics-covid-codelist-notebook",
        "medicines-seasonality-notebook",
        "one-drug-database-analysis",
        "cvd-covid-codelist-notebook",
        "doacs-prescribing-notebook",
        "ranitidine-shortages-notebook",
        "raas-covid-codelist-notebook",
        "statins-covid-codelist-notebook",
        "medicines-and-poisoning-notebook",
        "diabetes-drugs-covid-codelist-notebook",
        "bnf-less-suitable-for-prescribing",
        "insulin-covid-codelist-notebook",
        "respiratory-meds-covid-codelist-notebook",
        "immunosuppressant-covid-codelist-notebook",
        "top-10-notebook",
        "cusum-for-opioids-notebook",
        "steroids-covid-codelist-notebook",
        "chloroquine-covid-codelist-notebook",
        "antibiotics-non-oral-routes-notebook",
        "nhsdigital-shieldedrules-covid-codelist-methodology",
        "anticoagulant-covid-codelist-notebook",
        "repeat-prescribing-pandemic-covid-notebook",
        "devon-formulary-adherence-notebook",
        "statins-dose-paper",
        "covid19_results_reporting",
        "euctr_data_quality",
        "factors-associated-with-changing-notebook",
        "lidocaine-change-detection-notebook",
        "datalab-notebook-template",
        "antidepressant-trends",
        "mortality_tracking-covid-notebook",
        "ppi-covid-codelist-notebook",
        "openpath-dash",
        "fdaaa_requirements",
        "openpath-pipeline",
        "qof-data",
        "nhstrusts",
    ],
    "opensafely-core": [
        "matching",
        "scribe",
    ],
}
