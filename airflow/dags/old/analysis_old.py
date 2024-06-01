# from airflow import DAG
# from airflow.operators.python_operator import PythonOperator
# from sqlalchemy import create_engine, MetaData, Table
# from sqlalchemy.orm import sessionmaker
# from datetime import datetime
# import logging
# import random
# import uuid

# # Define default arguments
# default_args = {
#     'owner': 'airflow',
#     'depends_on_past': False,
#     'start_date': datetime(2023, 1, 1),
#     'email_on_failure': False,
#     'email_on_retry': False,
#     'retries': 1,
# }

# # Define the DAG
# dag = DAG(
#     'domain_analysis_full',  # Unique DAG ID
#     default_args=default_args,
#     description='Fetch data from domain_registered, insert analysis into domain_analysis and url_analysis, and log the results',
#     schedule_interval='@hourly',
#     max_active_runs=1,
#     concurrency=1,
# )

# # Database connection string
# conn_string = 'postgresql+psycopg2://airflow:airflow@postgres:5432/airflow'
# engine = create_engine(conn_string)
# Session = sessionmaker(bind=engine)
# metadata = MetaData(bind=engine)
# metadata.reflect(schema='analysis')

# def fetch_domains(ti):
#     try:
#         logging.info("Starting to fetch domains")
#         session = Session()
#         domain_registered = Table('domain_registered', metadata, autoload_with=engine, schema='analysis')
#         domains = session.query(domain_registered).all()
#         session.close()
#         logging.info("Fetched domains")
#         # Push the fetched domains to XCom
#         ti.xcom_push(key='domains', value=[(str(d.id), d.domain) for d in domains])
#         logging.info(f"Domains pushed to XCom: {[d.domain for d in domains]}")
#     except Exception as e:
#         logging.error(f"Error fetching domains: {e}")
#         raise
# def analyze_domains(**kwargs):
#     ti = kwargs['ti']
#     domains = ti.xcom_pull(key='domains', task_ids='fetch_domains')
#     logging.info(f"Domains to analyze: {domains}")
#     session = Session()
#     for domain in domains:
#         analyze_domain(session, domain)
#     session.close()

    
# def analyze_domain(session, domain):
#     try:
#         domain_id, domain_name = domain
#         cname = random.choice([True, False])
#         mx = random.choice([True, False])
#         domain_analysis = Table('domain_analysis', metadata, autoload_with=engine, schema='analysis')
#         session.execute(domain_analysis.insert().values(
#             id=str(uuid.uuid4()),
#             domain_id=domain_id,
#             domain=domain_name,
#             cname=cname,
#             mx=mx,
#             dt_update=datetime.now()
#         ))
#         logging.info(f"Inserted analysis into domain_analysis for domain {domain_name}")

#         session.commit()
#         logging.info(f"Database session committed for domain {domain_name}")
#     except Exception as e:
#         logging.error(f"Error analyzing domain {domain_name}: {e}")
#         session.rollback()
#         raise



# # Define tasks
# fetch_domains_task = PythonOperator(
#     task_id='fetch_domains',
#     python_callable=fetch_domains,
#     provide_context=True,
#     dag=dag,
# )

# analyze_domains_task = PythonOperator(
#     task_id='analyze_domains',
#     python_callable=analyze_domains,
#     provide_context=True,
#     dag=dag,
# )

# # Set task dependencies
# fetch_domains_task >> analyze_domains_task
