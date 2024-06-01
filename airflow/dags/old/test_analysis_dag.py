from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import datetime
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
import logging
import random
import uuid

# Configuration
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.now(),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
}

conn_string = 'postgresql+psycopg2://airflow:airflow@postgres:5432/airflow'

def fetch_domains():
    try:
        logging.info("Starting to fetch domains")
        engine = create_engine(conn_string)
        Session = sessionmaker(bind=engine)
        metadata = MetaData(bind=engine)
        metadata.reflect(schema='analysis')
        session = Session()
        domain_registered = Table('domain_registered', metadata, autoload_with=engine, schema='analysis')
        domains = session.query(domain_registered).all()
        session.close()
        logging.info("Fetched domains")
        return [(str(d.id), d.domain) for d in domains]
    except Exception as e:
        logging.error(f"Error fetching domains: {e}")
        raise

def iterate_domains(domains):
    engine = create_engine(conn_string)
    Session = sessionmaker(bind=engine)
    session = Session()
    metadata = MetaData(bind=engine)
    metadata.reflect(schema='analysis')
    logging.info(f"Domains to analyze: {domains}")
    for domain in domains:
        analyze_domain(session, domain, metadata)
    session.close()

def analyze_domain(session, domain, metadata):
    logging.info(f"Analyzing domain {domain}")
    try:
        domain_id, domain_name = domain
        cname = random.choice([True, False])
        mx = random.choice([True, False])
        dt_now = datetime.now()

        domain_analysis = Table('domain_analysis', metadata, autoload_with=engine, schema='analysis')

        existing_domain_analysis = session.query(domain_analysis).filter_by(domain_id=domain_id).first()

        if existing_domain_analysis:
            session.execute(
                domain_analysis.update()
                .where(domain_analysis.c.domain_id == domain_id)
                .values(
                    domain=domain_name,
                    cname=cname,
                    mx=mx,
                    dt_update=dt_now
                )
            )
            logging.info(f"Updated analysis in domain_analysis for domain {domain_name}")
        else:
            session.execute(domain_analysis.insert().values(
                id=str(uuid.uuid4()),
                domain_id=domain_id,
                domain=domain_name,
                cname=cname,
                mx=mx,
                dt_update=dt_now
            ))
            logging.info(f"Inserted analysis in domain_analysis for domain {domain_name}")

        session.commit()
        logging.info(f"Database session committed for domain {domain_name}")
    except Exception as e:
        logging.error(f"Error analyzing domain {domain_name}: {e}")
        session.rollback()
        raise

with DAG(
    'test_analysis', 
    default_args=default_args,
    description='Fetch data from domain_registered, insert analysis into domain_analysis and url_analysis, and log the results',
    schedule_interval='@hourly',
    max_active_runs=1,
    concurrency=1,
) as dag:

    fetch_domains_task = PythonOperator(
        task_id='fetch_domains',
        python_callable=fetch_domains,
    )

    analyze_domains_task = PythonOperator(
        task_id='analyze_domains',
        python_callable=iterate_domains,
        op_args=[fetch_domains_task.output],
    )

    fetch_domains_task >> analyze_domains_task
