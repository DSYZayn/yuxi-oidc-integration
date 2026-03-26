auth_router.py 的 OIDC 集成补丁

使用方法：
1. 在 auth_router.py 的导入部分添加以下导入：

```python
# OIDC 认证相关导入
from server.utils.oidc_config import oidc_config
from server.utils.oidc_utils import OIDCUtils
from server.routers.auth_router_oidc import (
    get_oidc_config_handler,
    oidc_callback_handler,
    oidc_login_url_handler,
    OIDCConfigResponse,
    OIDCLoginResponse,
)
```

2. 在 auth_router.py 文件末尾（在 auth 路由器定义之后）添加以下路由：

```python
# =============================================================================
# === OIDC 认证分组 ===
# =============================================================================

@auth.get("/oidc/config", response_model=OIDCConfigResponse)
async def get_oidc_config():
    \"\"\"获取 OIDC 配置（供前端使用）\"\"\"
    return await get_oidc_config_handler()


@auth.get("/oidc/login-url")
async def get_oidc_login_url(redirect_path: str = "/"):
    \"\"\"获取 OIDC 登录 URL\"\"\"
    return await oidc_login_url_handler(redirect_path)


@auth.get("/oidc/callback", response_model=OIDCLoginResponse)
async def oidc_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    \"\"\"处理 OIDC 回调\"\"\"
    return await oidc_callback_handler(None, code, state, db)
```

3. 确保在 backend/server/utils/__init__.py 中导出 OIDC 相关模块（如果需要）。

4. 安装依赖：在 backend/pyproject.toml 中添加 httpx 依赖：

```toml
[project]
dependencies = [
    # ... 其他依赖
    "httpx>=0.27.0",
]
```

或者运行：
```bash
cd backend
uv add httpx
```

5. 更新 .env 文件，添加 OIDC 配置（参考 .env.template 中的 OIDC 部分）。

6. 如果需要支持 OIDC 用户的头像，可以修改 create_oidc_user 函数来从 userinfo 中提取头像 URL。

7. 可选：添加 OIDC 登出功能

```python
@auth.post("/oidc/logout")
async def oidc_logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    \"\"\"OIDC 登出 - 返回 OIDC Provider 的登出 URL\"\"\"
    # 获取用户的 ID Token（需要在登录时保存）
    # 这里简化处理，直接返回登出 URL
    logout_url = await OIDCUtils.build_logout_url()
    return {"logout_url": logout_url}
```

注意：
- OIDC 用户的 user_id 格式为 "oidc:{sub}"，其中 sub 是 OIDC Provider 返回的唯一标识
- OIDC 用户没有密码，不能通过普通登录方式登录
- OIDC 用户的手机号字段为空
- 如果禁用自动创建用户，新用户将无法登录，需要管理员手动创建用户并设置其 user_id 为 "oidc:{sub}"
