#!/bin/bash

# ==============================================================================
# Script dừng Web Dashboard (Production: Nginx + Systemd Services)
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}  ĐANG DỪNG HỆ THỐNG PRODUCTION (SYSTEMD SERVICES)                     ${NC}"
echo -e "${BLUE}======================================================================${NC}"

echo -e "${YELLOW}Dừng fraud-backend service...${NC}"
sudo systemctl stop fraud-backend
echo -e "${GREEN}  ✓ Backend đã dừng.${NC}"

echo -e "${YELLOW}Dừng fraud-sync-gold service...${NC}"
sudo systemctl stop fraud-sync-gold
echo -e "${GREEN}  ✓ Sync Gold daemon đã dừng.${NC}"

# Dọn dẹp nếu còn tiến trình dev cũ
if lsof -ti:8000 >/dev/null 2>&1; then
    kill -9 $(lsof -ti:8000) 2>/dev/null || true
fi
if lsof -ti:5173 >/dev/null 2>&1; then
    kill -9 $(lsof -ti:5173) 2>/dev/null || true
fi

echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}  Đã dừng toàn bộ dịch vụ thành công!                                 ${NC}"
echo -e "${BLUE}======================================================================${NC}"
