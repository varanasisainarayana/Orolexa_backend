#!/bin/bash

# Dental AI API Deployment Script
# Usage: ./deploy.sh [production|staging|local]

set -e

ENVIRONMENT=${1:-local}
echo "Deploying to $ENVIRONMENT environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p uploads/profiles uploads/thumbnails

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    if [ -f env.production.example ]; then
        print_warning "No .env file found. Copying from env.production.example..."
        cp env.production.example .env
        print_warning "Please update .env file with your actual values before deploying!"
    else
        print_error "No .env file found and no example file available."
        exit 1
    fi
fi

# Build and deploy based on environment
case $ENVIRONMENT in
    "production")
        print_status "Deploying to production..."
        
        # Stop existing containers
        docker-compose down
        
        # Build and start with production settings
        docker-compose up -d --build
        
        print_status "Production deployment completed!"
        print_status "API is running on http://localhost:8000"
        print_status "Health check: http://localhost:8000/health"
        ;;
        
    "staging")
        print_status "Deploying to staging..."
        
        # Stop existing containers
        docker-compose down
        
        # Build and start with staging settings
        docker-compose up -d --build
        
        print_status "Staging deployment completed!"
        print_status "API is running on http://localhost:8000"
        print_status "Health check: http://localhost:8000/health"
        ;;
        
    "local"|*)
        print_status "Deploying locally..."
        
        # Stop existing containers
        docker-compose down
        
        # Build and start with local settings
        docker-compose up -d --build
        
        print_status "Local deployment completed!"
        print_status "API is running on http://localhost:8000"
        print_status "Health check: http://localhost:8000/health"
        ;;
esac

# Wait for service to be ready
print_status "Waiting for service to be ready..."
sleep 10

# Check health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Health check passed! Service is running successfully."
else
    print_error "Health check failed! Service might not be running properly."
    print_status "Check logs with: docker-compose logs"
    exit 1
fi

print_status "Deployment completed successfully!"
print_status "To view logs: docker-compose logs -f"
print_status "To stop: docker-compose down"
