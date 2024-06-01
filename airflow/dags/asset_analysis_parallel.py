import sys
import os
from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor

# Atualizando o caminho para o diretório correto dos operadores personalizados
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operators.analysis import DomainAnalysisOperator

conn_string = 'postgresql+psycopg2://airflow:airflow@postgres:5432/airflow'

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),  # Ajuste para a data inicial adequada
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

def fetch_domains(**kwargs):
    try:
        logging.info("Starting to fetch domains")
        engine = create_engine(conn_string)
        Session = sessionmaker(bind=engine)
        metadata = MetaData(bind=engine)
        metadata.reflect(schema='analysis')
        session = Session()
        domain_results = Table('domain_results', metadata, autoload_with=engine, schema='analysis')
        domain_registered = Table('domain_registered', metadata, autoload_with=engine, schema='analysis')
        query = session.query(domain_results.c.id, domain_results.c.domain_result, domain_registered.c.domain) \
                        .join(domain_registered, domain_results.c.domain_id == domain_registered.c.id)
        domains = query.all()
        session.close()
        logging.info("Fetched domains")
        domains_to_analyze = [(str(d.id), d.domain_result, d.domain) for d in domains]
        kwargs['ti'].xcom_push(key='domains', value=domains_to_analyze)
    except Exception as e:
        logging.error(f"Error fetching domains: {e}")
        raise

def analyze_domain(domain):
    try:
        domain_result_id, domain_result, original_domain = domain
        logging.info(f"Analyzing domain: {domain_result} with original domain: {original_domain}")
        result = DomainAnalysisOperator.compare_urls(original_domain, domain_result)
        return (domain_result_id, domain_result, original_domain, result)
    except Exception as e:
        logging.error(f"Error analyzing domain: {domain_result}, error: {e}")
        raise

def analyze_domains(**kwargs):
    try:
        domains = kwargs['ti'].xcom_pull(key='domains', task_ids='fetch_domains_task')
        analysis_results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(analyze_domain, domain) for domain in domains]
            for future in futures:
                analysis_results.append(future.result())
        
        kwargs['ti'].xcom_push(key='analysis_results', value=analysis_results)
    except Exception as e:
        logging.error(f"Error analyzing domains: {e}")
        raise

def persist_domain_analysis(**kwargs):
    try:
        analysis_results = kwargs['ti'].xcom_pull(key='analysis_results', task_ids='analyze_domains_task')
        engine = create_engine(conn_string)
        Session = sessionmaker(bind=engine)
        session = Session()
        metadata = MetaData(bind=engine)
        metadata.reflect(schema='analysis')
        
        domain_analysis_table = Table('domain_analysis', metadata, autoload_with=engine, schema='analysis')
        
        for result in analysis_results:
            domain_result_id, domain_result, original_domain, analysis = result
            logging.info(f"Persisting domain analysis for: {domain_result}")
            session.execute(
                domain_analysis_table.insert().values(
                    domain_result_id=domain_result_id,
                    domain=domain_result,
                    matchwebcontent=analysis.get('matchWebContent', False),
                    matchfavicon=analysis.get('matchFavicon', False),
                    mx=analysis.get('mx', False),
                    score=analysis.get('score', 0),
                    dt_update=datetime.now()
                )
            )
        session.commit()
        session.close()
    except Exception as e:
        logging.error(f"Error persisting domain analysis: {e}")
        session.rollback()
        raise

def persist_url_analysis(**kwargs):
    try:
        analysis_results = kwargs['ti'].xcom_pull(key='analysis_results', task_ids='analyze_domains_task')
        engine = create_engine(conn_string)
        Session = sessionmaker(bind=engine)
        session = Session()
        metadata = MetaData(bind=engine)
        metadata.reflect(schema='analysis')
        
        url_analysis_table = Table('url_analysis', metadata, autoload_with=engine, schema='analysis')
        
        for result in analysis_results:
            domain_result_id, domain_result, original_domain, analysis = result
            logging.info(f"Persisting URL analysis for: {url}")
            session.execute(url_analysis_table.insert().values(
                    domain_result_id=domain_result_id,
                    url=result.get('url', False),
                    alive=result.get('alive', False),
                    dt_update=datetime.now()
                )
            )
        session.commit()
        session.close()
    except Exception as e:
        logging.error(f"Error persisting URL analysis: {e}")
        session.rollback()
        raise

with DAG(
    'soc_domain_analysis_parallel', 
    default_args=default_args,
    description='Fetch data from domain_registered, insert analysis into domain_analysis and url_analysis, and log the results',
    schedule_interval='@hourly',
    max_active_runs=1,
    concurrency=1,
) as dag:

    fetch_domains_task = PythonOperator(
        task_id='fetch_domains_task',
        python_callable=fetch_domains,
        provide_context=True,
    )

    analyze_domains_task = PythonOperator(
        task_id='analyze_domains_task',
        python_callable=analyze_domains,
        provide_context=True,
    )

    persist_domain_analysis_task = PythonOperator(
        task_id='persist_domain_analysis_task',
        python_callable=persist_domain_analysis,
        provide_context=True,
    )

    persist_url_analysis_task = PythonOperator(
        task_id='persist_url_analysis_task',
        python_callable=persist_url_analysis,
        provide_context=True,
    )

    fetch_domains_task >> analyze_domains_task >> [persist_domain_analysis_task, persist_url_analysis_task]
