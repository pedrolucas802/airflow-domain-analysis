FROM apache/airflow:latest

USER airflow

RUN pip install apache-airflow[postgres]

ENV AIRFLOW_HOME=/opt/airflow

COPY ./dags /opt/airflow/dags

ENTRYPOINT ["airflow", "standalone"]

EXPOSE 8080