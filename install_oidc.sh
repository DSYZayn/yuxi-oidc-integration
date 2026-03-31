#!/bin/bash
# Yuxi-Know OIDC 认证集成安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息函数
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查目标目录
if [ -z "$1" ]; then
    error "请指定 Yuxi-Know 项目目录"
    echo "用法: $0 <path-to-yuxi-know-project>"
    exit 1
fi

TARGET_DIR="$1"

if [ ! -d "$TARGET_DIR" ]; then
    error "目标目录不存在: $TARGET_DIR"
    exit 1
fi

info "开始安装 OIDC 认证集成..."
info "目标目录: $TARGET_DIR"

# 检查必要的目录结构
if [ ! -d "$TARGET_DIR/backend" ] || [ ! -d "$TARGET_DIR/web" ]; then
    error "目标目录不是有效的 Yuxi-Know 项目目录"
    exit 1
fi

# =============================================================================
# 后端安装
# =============================================================================
info "安装后端 OIDC 组件..."

# 创建必要的目录
mkdir -p "$TARGET_DIR/backend/server/utils"
mkdir -p "$TARGET_DIR/backend/server/routers"

# 复制后端文件
if [ -f "$SCRIPT_DIR/backend/server/utils/oidc_config.py" ]; then
    cp "$SCRIPT_DIR/backend/server/utils/oidc_config.py" "$TARGET_DIR/backend/server/utils/"
    info "已安装: backend/server/utils/oidc_config.py"
fi

if [ -f "$SCRIPT_DIR/backend/server/utils/oidc_utils.py" ]; then
    cp "$SCRIPT_DIR/backend/server/utils/oidc_utils.py" "$TARGET_DIR/backend/server/utils/"
    info "已安装: backend/server/utils/oidc_utils.py"
fi

if [ -f "$SCRIPT_DIR/backend/server/routers/auth_router_oidc.py" ]; then
    cp "$SCRIPT_DIR/backend/server/routers/auth_router_oidc.py" "$TARGET_DIR/backend/server/routers/"
    info "已安装: backend/server/routers/auth_router_oidc.py"
fi
# 覆盖 auth_router.py
if [ -f "$SCRIPT_DIR/backend/server/routers/auth_router.py" ]; then
    cp "$SCRIPT_DIR/backend/server/routers/auth_router.py" "$TARGET_DIR/backend/server/routers/auth_router.py"
    info "已覆盖: backend/server/routers/auth_router.py"
fi


# =============================================================================
# 前端安装
# =============================================================================
info "安装前端 OIDC 组件..."

# 创建必要的目录
mkdir -p "$TARGET_DIR/web/src/apis"
mkdir -p "$TARGET_DIR/web/src/views"

# 复制前端文件
if [ -f "$SCRIPT_DIR/web/src/apis/auth_api.js" ]; then
    cp "$SCRIPT_DIR/web/src/apis/auth_api.js" "$TARGET_DIR/web/src/apis/"
    info "已安装: web/src/apis/auth_api.js"
fi

if [ -f "$SCRIPT_DIR/web/src/views/OIDCCallbackView.vue" ]; then
    cp "$SCRIPT_DIR/web/src/views/OIDCCallbackView.vue" "$TARGET_DIR/web/src/views/"
    info "已安装: web/src/views/OIDCCallbackView.vue"
fi

# 覆盖登录页面
if [ -f "$SCRIPT_DIR/web/src/views/LoginView_oidc.vue" ]; then
    cp "$SCRIPT_DIR/web/src/views/LoginView_oidc.vue" "$TARGET_DIR/web/src/views/LoginView.vue"
    info "已覆盖: web/src/views/LoginView.vue"
fi
# =============================================================================
# 更新 .env.template
# =============================================================================
info "更新环境变量模板..."

if [ -f "$SCRIPT_DIR/.env.template" ]; then
    # 备份原文件
    if [ -f "$TARGET_DIR/.env.template" ]; then
        cp "$TARGET_DIR/.env.template" "$TARGET_DIR/.env.template.backup.$(date +%Y%m%d%H%M%S)"
        info "已备份原 .env.template"
    fi
    cp "$SCRIPT_DIR/.env.template" "$TARGET_DIR/.env.template"
    info "已更新: .env.template"
fi

# =============================================================================
# 提示信息
# =============================================================================
echo ""
echo "========================================"
echo -e "${GREEN}OIDC 认证集成安装完成！${NC}"
echo "========================================"
echo ""
echo "请完成以下步骤："
echo ""
echo "1. 添加前端路由:"
echo "   编辑 $TARGET_DIR/web/src/router/index.js"
echo "   添加 OIDC 回调路由:"
echo '   {'
echo '     path: "/auth/oidc/callback",'
echo '     name: "OIDCCallback",'
echo '     component: () => import("@/views/OIDCCallbackView.vue"),'
echo '     meta: { public: true }'
echo '   }'
echo ""
echo "2. 配置环境变量:"
echo "   编辑 $TARGET_DIR/.env 文件，添加 OIDC 配置"
echo "   参考 .env.template 中的 OIDC 部分"
echo ""
echo "5. 重启服务:"
echo "   后端: cd $TARGET_DIR/backend && uv run python -m server.main"
echo "   前端: cd $TARGET_DIR/web && pnpm dev"
echo ""
echo "详细文档请参考: $SCRIPT_DIR/README.md"
echo ""
