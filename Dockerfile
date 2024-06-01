FROM apache/airflow:latest

USER airflow

RUN pip install apache-airflow[postgres]

RUN pip install whois

ENV AIRFLOW_HOME=/opt/airflow

COPY airflow/dags /opt/airflow/dags

EXPOSE 8080
