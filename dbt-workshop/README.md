## Getting started

```bash
cd dbt-workshop/
python -m venv VENV
pip install -r requirements.txt
cp profiles.yml.example profiles.yml
```

set there
- **project**: GCP PROJECT ID
- **dataset**: workshop_<your-last-name> i.e. workshop_kruglov
- **location**: europe-west4


```bash
dbt run-operation setup_resources
```
