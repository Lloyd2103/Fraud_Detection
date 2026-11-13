#!/bin/bash

# ==============================================================================
# Script khởi động Web Dashboard (Production: Nginx + Systemd Services)
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  KHỞI ĐỘNG HỆ THỐNG PRODUCTION (NGINX + SYSTEMD SERVICES)            ${NC}"
echo -e "${BLUE}======================================================================${NC}"

echo -e "${YELLOW}[1/3] Khởi động Nginx Reverse Proxy (SSL/HTTPS)...${NC}"
sudo systemctl restart nginx
if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}  ✓ Nginx đang chạy (Ports 80 -> 443 HTTPS)${NC}"
else
    echo -e "${RED}  ✗ Nginx gặp lỗi!${NC}"
    sudo systemctl status nginx --no-pager
    exit 1
fi

echo -e "${YELLOW}[2/3] Khởi động Backend Uvicorn Service (fraud-backend)...${NC}"
sudo systemctl restart fraud-backend
if sudo systemctl is-active --quiet fraud-backend; then
    echo -e "${GREEN}  ✓ Backend đang chạy ổn định (127.0.0.1:8000)${NC}"
else
    echo -e "${RED}  ✗ Backend gặp lỗi!${NC}"
    sudo systemctl status fraud-backend --no-pager
    exit 1
fi

echo -e "${YELLOW}[3/3] Khởi động Sync Gold Daemon (fraud-sync-gold)...${NC}"
sudo systemctl restart fraud-sync-gold
if sudo systemctl is-active --quiet fraud-sync-gold; then
    echo -e "${GREEN}  ✓ Sync Gold Daemon đang chạy ổn định (Delta CDF -> CockroachDB)${NC}"
else
    echo -e "${RED}  ✗ Sync Gold Daemon gặp lỗi!${NC}"
    sudo systemctl status fraud-sync-gold --no-pager
    exit 1
fi

echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}  ĐÃ KHỞI ĐỘNG THÀNH CÔNG HỆ THỐNG PRODUCTION!                        ${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo -e "  - ${YELLOW}Giao diện Web (HTTPS):${NC}  https://192.168.80.200 hoặc https://localhost"
echo -e "  - ${YELLOW}Backend API Docs:${NC}       https://192.168.80.200/docs"
echo -e "  - ${YELLOW}Kiểm tra trạng thái:${NC}    sudo systemctl status fraud-backend fraud-sync-gold nginx"
echo -e "  - ${YELLOW}Dừng dịch vụ:${NC}           ./stop.sh"
echo -e "${BLUE}======================================================================${NC}"
