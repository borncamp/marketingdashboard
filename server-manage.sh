#!/bin/bash

###############################################################################
# Server Management Script for Marketing Campaign Tracker
# Quick access to common server operations
###############################################################################

SERVER_USER="root"
SERVER_IP="46.224.115.100"
APP_DIR="/opt/marketing-tracker"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_help() {
    echo "Marketing Campaign Tracker - Server Management"
    echo ""
    echo "Usage: ./server-manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  logs          - View application logs"
    echo "  logs-f        - Follow application logs in real-time"
    echo "  status        - Show container status"
    echo "  restart       - Restart all services"
    echo "  restart-be    - Restart backend only"
    echo "  restart-fe    - Restart frontend only"
    echo "  stop          - Stop all services"
    echo "  start         - Start all services"
    echo "  ssh           - SSH into the server"
    echo "  update-env    - Update .env file on server"
    echo "  rebuild       - Rebuild and restart containers"
    echo "  stats         - Show Docker resource usage"
    echo "  cleanup       - Clean up unused Docker resources"
    echo "  backup        - Backup configuration files"
    echo "  health        - Check application health"
    echo ""
}

run_command() {
    case $1 in
        logs)
            echo -e "${GREEN}Fetching logs...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose logs --tail=100"
            ;;
        logs-f)
            echo -e "${GREEN}Following logs (Ctrl+C to exit)...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose logs -f"
            ;;
        status)
            echo -e "${GREEN}Container status:${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose ps"
            ;;
        restart)
            echo -e "${YELLOW}Restarting all services...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose restart"
            echo -e "${GREEN}✓ Services restarted${NC}"
            ;;
        restart-be)
            echo -e "${YELLOW}Restarting backend...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose restart backend"
            echo -e "${GREEN}✓ Backend restarted${NC}"
            ;;
        restart-fe)
            echo -e "${YELLOW}Restarting frontend...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose restart frontend"
            echo -e "${GREEN}✓ Frontend restarted${NC}"
            ;;
        stop)
            echo -e "${YELLOW}Stopping all services...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose down"
            echo -e "${GREEN}✓ Services stopped${NC}"
            ;;
        start)
            echo -e "${GREEN}Starting all services...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose up -d"
            echo -e "${GREEN}✓ Services started${NC}"
            ;;
        ssh)
            echo -e "${GREEN}Connecting to server...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP}
            ;;
        update-env)
            if [ ! -f .env ]; then
                echo -e "${RED}Error: .env file not found locally${NC}"
                exit 1
            fi
            echo -e "${YELLOW}Updating .env file on server...${NC}"
            scp .env ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/.env
            echo -e "${GREEN}✓ .env updated${NC}"
            echo -e "${YELLOW}Restarting services to apply changes...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose restart"
            echo -e "${GREEN}✓ Services restarted${NC}"
            ;;
        rebuild)
            echo -e "${YELLOW}Rebuilding and restarting containers...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose down && docker-compose up -d --build"
            echo -e "${GREEN}✓ Containers rebuilt and started${NC}"
            ;;
        stats)
            echo -e "${GREEN}Docker resource usage:${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "docker stats --no-stream"
            ;;
        cleanup)
            echo -e "${YELLOW}Cleaning up unused Docker resources...${NC}"
            ssh ${SERVER_USER}@${SERVER_IP} "docker system prune -f"
            echo -e "${GREEN}✓ Cleanup complete${NC}"
            ;;
        backup)
            echo -e "${GREEN}Backing up configuration...${NC}"
            mkdir -p ./backup
            scp ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/.env ./backup/.env.backup-$(date +%Y%m%d-%H%M%S)
            echo -e "${GREEN}✓ Backup saved to ./backup/${NC}"
            ;;
        health)
            echo -e "${GREEN}Checking application health...${NC}"
            echo ""
            echo "Backend health:"
            curl -s http://${SERVER_IP}:8000/health | python3 -m json.tool || echo "Backend not responding"
            echo ""
            echo ""
            echo "Frontend status:"
            curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://${SERVER_IP}:3000
            echo ""
            echo "Container status:"
            ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose ps"
            ;;
        *)
            show_help
            ;;
    esac
}

# Main
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

run_command $1
