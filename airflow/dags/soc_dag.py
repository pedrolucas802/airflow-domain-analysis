import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operators.analysis import DomainAnalysisOperator

from datetime import datetime
from airflow import DAG
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
import logging
import whois
from airflow.operators.python_operator import PythonOperator 


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.now(),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}


def domain_analysis():
    try:
        logging.info("Starting to fetch soc")
        result = DomainAnalysisOperator.query_domain("google.com")
        logging.info("RESULT ------>" + result.get('mx'))
        logging.info(result)
        
        return result
    except Exception as e:
        logging.error(f"Error fetching domains: {e}")
        raise

with DAG(
    'soc_domain_analysis', 
    default_args=default_args,
    description='Fetch data from domain_registered, insert analysis into domain_analysis and url_analysis, and log the results',
    schedule_interval='@hourly',
    max_active_runs=1,
    concurrency=1,
) as dag:

    domain_analysis = PythonOperator(
        task_id='domain_analysis',
        python_callable=domain_analysis,
    )

    domain_analysis 
