import sys
import os
from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker

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

def fetch_analyze_persist_domains(**kwargs):
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
        
        domain_analysis_table = Table('domain_analysis', metadata, autoload_with=engine, schema='analysis')
        url_analysis_table = Table('url_analysis', metadata, autoload_with=engine, schema='analysis')
        
        logging.info("Fetched domains")
        
        for domain in domains:
            domain_result_id, domain_result, original_domain = domain
            logging.info(f"Analyzing domain: {domain_result} with original domain: {original_domain}")
            result = DomainAnalysisOperator.compare_urls(original_domain, domain_result)
            
            logging.info(f"Persisting domain analysis for: {domain_result}")
            session.execute(
                domain_analysis_table.insert().values(
                    domain_result_id=domain_result_id,
                    domain=domain_result,
                    matchwebcontent=result.get('matchWebContent', False),
                    matchfavicon=result.get('matchFavicon', False),
                    mx=result.get('mx', False),
                    score=result.get('score', 0),
                    dt_update=datetime.now()
                )
            )
            
            logging.info(f"Persisting URL analysis for: {domain_result}")
            session.execute(
                url_analysis_table.insert().values(
                    domain_result_id=domain_result_id,
                    url=result.get('url', False),
                    alive=result.get('alive', False),
                    dt_update=datetime.now()
                )
            )
        
        session.commit()
        session.close()
    except Exception as e:
        logging.error(f"Error fetching, analyzing, or persisting domains: {e}")
        session.rollback()
        raise

with DAG(
    'soc_domain_analysis_procedural', 
    default_args=default_args,
    description='Fetch, analyze, and persist domain and URL analysis',
    schedule_interval='@hourly',
    max_active_runs=1,
    concurrency=1,
) as dag:

    fetch_analyze_persist_task = PythonOperator(
        task_id='fetch_analyze_persist_task',
        python_callable=fetch_analyze_persist_domains,
        provide_context=True,
    )

    fetch_analyze_persist_task
