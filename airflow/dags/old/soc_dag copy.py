# import sys
# import os
# from datetime import datetime
# import logging
# from airflow import DAG
# from airflow.operators.python_operator import PythonOperator

# # Ensure the correct import path for your operators
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# from operators.analysis import DomainAnalysisOperator

# default_args = {
#     'owner': 'airflow',
#     'depends_on_past': False,
#     'start_date': datetime.now(),
#     'email_on_failure': False,
#     'email_on_retry': False,
#     'retries': 0,
# }

# def compare_domain_urls():
#     try:
#         logging.info("Starting to compare domains")
#         result = DomainAnalysisOperator.compare_urls("google.com", "go0gle.com")
#         logging.info("COMPARE RESULT ------>")
#         logging.info(result)
        
#         return result
#     except Exception as e:
#         logging.error(f"Error comparing domains: {e}")
#         raise

# with DAG(
#     'soc_domain_analysis', 
#     default_args=default_args,
#     description='Fetch data from domain_registered, insert analysis into domain_analysis and url_analysis, and log the results',
#     schedule_interval='@hourly',
#     max_active_runs=1,
#     concurrency=1,
# ) as dag:

#     compare_domain_urls_task = PythonOperator(
#         task_id='compare_domain_urls',
#         python_callable=compare_domain_urls,
#     )

#     compare_domain_urls_task
