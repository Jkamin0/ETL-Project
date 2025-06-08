#!/bin/bash

echo "Setting up Steam Games ETL Pipeline..."

# Create necessary directories
mkdir -p dags logs plugins

# Set proper permissions
export AIRFLOW_UID=$(id -u)
echo "AIRFLOW_UID=$AIRFLOW_UID" > .env

# Create directories with proper ownership
sudo chown -R $AIRFLOW_UID:0 dags logs plugins

echo "Building and starting services..."

# Build and run
docker-compose up -d airflow-init
docker-compose up -d

echo ""
echo "Setup complete!"
echo ""
echo "Access Airflow UI at: http://localhost:8080"
echo "Username: admin"
echo "Password: admin"
echo ""
echo "PostgreSQL is available at localhost:5432"
echo "Database: airflow"
echo "Username: airflow" 
echo "Password: airflow"
echo ""
echo "To check logs: docker-compose logs -f"
echo "To stop: docker-compose down"
echo "To restart: docker-compose restart"