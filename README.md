# Yuxi-Know OIDC 认证集成指南

本文档介绍如何为 Yuxi-Know 项目集成 OIDC (OpenID Connect) 认证登录功能。
(由于～～是纯vibe coding实现～～没时间写测试，所以没敢直接pr，而是以插件项目提供)
## 功能特性

- ✅ 支持标准 OIDC 协议
- ✅ 自动发现 OIDC Provider 配置
- ✅ 支持自动创建用户
- ✅ 所有参数通过环境变量配置
- ✅ 不影响原有账号体系
- ✅ 支持自定义用户名、邮箱、姓名映射字段
<img width="1920" height="913" alt="1774525090070_d" src="https://github.com/user-attachments/assets/6616b84d-c7b1-4960-9c19-d6e89b19bac8" />

<img width="2560" height="1359" alt="image" src="https://github.com/user-attachments/assets/beb2861e-2948-4894-ac8a-44986ce50b99" />

## 文件结构

```
yuxi-oidc-integration/
├── README.md                              # 本文件
├── .env.template                          # 更新后的环境变量模板
├── install_oidc.sh                        # 自动安装脚本
├── backend/
│   └── server/
│       ├── routers/
│       │   ├── auth_router_oidc.py        # OIDC 路由处理函数
│       │   └── auth_router.py             # auth_router.py 修改版
│       └── utils/
│           ├── oidc_config.py             # OIDC 配置模块
│           └── oidc_utils.py              # OIDC 工具类
└── web/
    └── src/
        ├── apis/
        │   └── auth_api.js                # 认证相关 API
        └── views/
            ├── LoginView_oidc.vue         # 登录页面（替换原 LoginView.vue）
            └── OIDCCallbackView.vue       # OIDC 回调处理页面
```

## 安装步骤
### 直接使用安装脚本
```bash
cd yuxi-oidc-integration
bash ./install_oidc.sh /path/to/your/yuxi-know-project
```

或者手动复制文件安装：

### 1. 复制后端文件

```bash
# 复制配置文件
cp backend/server/utils/oidc_config.py /path/to/your/project/backend/server/utils/
cp backend/server/utils/oidc_utils.py /path/to/your/project/backend/server/utils/

# 复制路由处理函数
cp backend/server/routers/auth_router_oidc.py /path/to/your/project/backend/server/routers/


# 替换原有 auth_router.py
cp backend/server/routers/auth_router.py /path/to/your/project/backend/server/routers/auth_router.py
```



### 2. 复制前端文件

```bash
# 复制 API 文件
cp web/src/apis/auth_api.js /path/to/your/project/web/src/apis/

# 复制视图文件
cp web/src/views/OIDCCallbackView.vue /path/to/your/project/web/src/views/

# 替换登录页面
cp web/src/views/LoginView_oidc.vue /path/to/your/project/web/src/views/LoginView.vue
```

### 3. 添加前端路由

> **这一步是必须手动完成的**，安装脚本不会自动修改宿主仓库的路由配置。

在 `web/src/router/index.js` 中注册 OIDC 回调路由。找到路由数组（通常为 `routes` 变量），添加以下条目：

```javascript
{
  path: '/auth/oidc/callback',
  name: 'OIDCCallback',
  component: () => import('@/views/OIDCCallbackView.vue'),
  meta: { public: true }
}
```

**要点说明：**

- `path` 必须与后端 `auth_router_oidc.py` 中的 `FRONTEND_CALLBACK_PATH` 常量保持一致（默认 `/auth/oidc/callback`）。  
  如需自定义路径，请同步修改两处。
- `meta: { public: true }` 确保路由守卫不会在登录完成前将用户重定向到登录页。  
  如果项目的路由守卫使用不同的字段标记公开路由，请按实际情况调整。

### 5. 配置环境变量

在 `.env` 文件中添加 OIDC 配置（参考 `.env.template` 中的 OIDC 部分）：

```bash
# 启用 OIDC
OIDC_ENABLED=true

# OIDC Provider 配置
OIDC_ISSUER_URL=https://your-oidc-provider.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret

# 回调 URL（可选，默认自动构建）
OIDC_REDIRECT_URI=https://your-app.com/api/auth/oidc/callback

# 请求的 scope
OIDC_SCOPES=openid profile email

# 自动创建用户
OIDC_AUTO_CREATE_USER=true

# 默认角色
OIDC_DEFAULT_ROLE=user

# 默认部门
OIDC_DEFAULT_DEPARTMENT=OIDC用户

# 字段映射
OIDC_USERNAME_CLAIM=preferred_username
OIDC_EMAIL_CLAIM=email
OIDC_NAME_CLAIM=name
```

### 6. 重启服务

```bash
# 重启后端服务
cd backend
uv run python -m server.main

# 重启前端服务
cd web
pnpm dev
```

```bash
# 如果已经启动了服务，请使用以下命令重启：
docker restart api-dev
docker restart web-dev
```

## OIDC 回调流程

集成采用**纯重定向**方式，后端不渲染任何 HTML，所有 UI 由前端 Vue 页面负责。

```
用户点击 SSO 登录
      │
      ▼
LoginView.vue 请求 /api/auth/oidc/login-url
      │
      ▼
浏览器跳转到 OIDC Provider 授权页
      │
      ▼（用户授权后）
OIDC Provider 回调 → GET /api/auth/oidc/callback?code=...&state=...
      │
      ├─ 认证失败 → 302 重定向到 /login?oidc_error=<错误信息>
      │                    │
      │                    ▼
      │             LoginView.vue 读取 oidc_error 参数并显示错误提示
      │
      └─ 认证成功 → 302 重定向到 /auth/oidc/callback?token=...&user_id=...&username=...
                           │
                           ▼
                    OIDCCallbackView.vue 读取 URL 参数
                    → 写入 localStorage / Pinia store
                    → 跳转到目标页面
```

**前端路由路径与后端常量的对应关系：**

| 说明 | 前端路由 `path` | 后端常量 |
|------|----------------|---------|
| 成功回调页 | `/auth/oidc/callback` | `FRONTEND_CALLBACK_PATH`（`auth_router_oidc.py`） |
| 错误重定向页 | `/login` | `FRONTEND_LOGIN_PATH`（`auth_router_oidc.py`） |

如需自定义路径，两处必须同步修改。

## 配置说明

### OIDC_ISSUER_URL

OIDC Provider 的 Issuer URL。系统会自动从此 URL 获取 OIDC 配置（通过 `/.well-known/openid-configuration`）。

示例：
- Keycloak: `https://keycloak.example.com/realms/myrealm`
- Auth0: `https://your-domain.auth0.com`
- Okta: `https://your-domain.okta.com`

### OIDC_CLIENT_ID 和 OIDC_CLIENT_SECRET

在 OIDC Provider 中注册应用时获得的客户端凭证。

### OIDC_REDIRECT_URI

回调 URL，需要确保此 URL 在 OIDC Provider 中已注册。

默认值为 `/api/auth/oidc/callback`，如果使用默认配置，需要确保：
- 前端访问的是 `/api/auth/oidc/callback`
- OIDC Provider 中注册的回调 URL 是 `https://your-app.com/api/auth/oidc/callback`

### OIDC_SCOPES

请求的 scope，默认为 `openid profile email`。

### OIDC_AUTO_CREATE_USER

是否自动创建用户。如果设置为 `false`，则只有已存在的用户才能登录（需要管理员手动创建用户并设置其 `user_id` 为 `oidc:{sub}`）。

### OIDC_DEFAULT_ROLE

OIDC 用户的默认角色，可选值为 `user` 或 `admin`。默认为 `user`。

### OIDC_DEFAULT_DEPARTMENT

OIDC 用户的默认部门名称。如果该部门不存在，系统会自动创建。

### OIDC_USERNAME_CLAIM / OIDC_EMAIL_CLAIM / OIDC_NAME_CLAIM

从 OIDC userinfo 中提取用户信息的字段映射。

## 用户数据格式

OIDC 用户在数据库中的存储格式：

- `user_id`: `oidc:{sub}`（sub 是 OIDC Provider 返回的唯一标识）
- `username`: 从 userinfo 中提取的显示名称
- `password_hash`: 随机生成的密码（OIDC 用户不能使用密码登录）
- `phone_number`: `null`
- `role`: 根据 `OIDC_DEFAULT_ROLE` 配置
- `department_id`: 根据 `OIDC_DEFAULT_DEPARTMENT` 配置

## 常见问题

### Q: OIDC 用户能否使用密码登录？

A: 不能。OIDC 用户的密码是随机生成的，只能通过 OIDC 方式登录。

### Q: 如何将现有用户关联到 OIDC 账号？

A: 需要管理员手动修改用户的 `user_id` 为 `oidc:{sub}` 格式，其中 `{sub}` 是 OIDC Provider 返回的用户唯一标识。

### Q: 如何禁用 OIDC 认证？

A: 将 `OIDC_ENABLED` 设置为 `false` 或删除相关环境变量，然后重启服务。

### Q: 支持哪些 OIDC Provider？

A: 理论上支持任何标准 OIDC Provider，包括：
- Keycloak
- Auth0
- Okta
- Azure AD
- Google Identity
- GitHub（通过 OIDC 兼容层）
- 自定义 OIDC Provider

### Q: 如何调试 OIDC 登录问题？

A: 可以查看后端日志，OIDC 相关的日志会包含 `OIDC` 关键字。也可以检查浏览器的网络请求，查看 OIDC 流程中的各个请求和响应。

## 安全建议

1. 使用 HTTPS 协议
2. 妥善保管 `OIDC_CLIENT_SECRET`
3. 定期轮换 OIDC 客户端密钥
4. 配置适当的 `OIDC_SCOPES`，不要请求不必要的权限
