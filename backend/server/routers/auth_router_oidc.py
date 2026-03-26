"""OIDC 认证路由模块

此模块包含 OIDC 认证相关的路由，需要被导入到主 auth_router.py 中使用。
"""
from fastapi import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from yuxi.utils import logger
from yuxi.storage.postgres.models_business import User, Department
from yuxi.repositories.user_repository import UserRepository
from yuxi.repositories.department_repository import DepartmentRepository
from server.utils.auth_utils import AuthUtils
from server.utils.user_utils import generate_unique_user_id
from server.utils.oidc_config import oidc_config
from server.utils.oidc_utils import OIDCUtils
from server.utils.common_utils import log_operation
from yuxi.utils.datetime_utils import utc_now_naive


# =============================================================================
# === OIDC 请求和响应模型 ===
# =============================================================================

class OIDCConfigResponse(BaseModel):
    """OIDC 配置响应"""
    enabled: bool
    login_url: str | None = None


class OIDCCallbackRequest(BaseModel):
    """OIDC 回调请求"""
    code: str
    state: str


class OIDCLoginResponse(BaseModel):
    """OIDC 登录响应"""
    access_token: str
    token_type: str
    user_id: int
    username: str
    user_id_login: str
    phone_number: str | None = None
    avatar: str | None = None
    role: str
    department_id: int | None = None
    department_name: str | None = None


# =============================================================================
# === OIDC 工具函数 ===
# =============================================================================

async def get_or_create_oidc_department(db) -> Department | None:
    """获取或创建 OIDC 用户的默认部门"""
    dept_name = oidc_config.default_department

    result = await db.execute(select(Department).filter(Department.name == dept_name))
    dept = result.scalar_one_or_none()

    if not dept:
        # 创建 OIDC 用户部门
        dept_repo = DepartmentRepository()
        dept = await dept_repo.create({
            "name": dept_name,
            "description": f"{dept_name}部门",
        })
        logger.info(f"Created OIDC department: {dept_name}")

    return dept


async def find_user_by_oidc_sub(db, sub: str) -> User | None:
    """通过 OIDC sub 查找用户"""
    # OIDC 用户的 user_id 格式为: oidc:{sub}
    oidc_user_id = f"oidc:{sub}"
    result = await db.execute(select(User).filter(User.user_id == oidc_user_id, User.is_deleted == 0))
    return result.scalar_one_or_none()


async def create_oidc_user(db, user_info: dict, department_id: int | None = None) -> User:
    """创建 OIDC 用户"""
    user_repo = UserRepository()

    sub = user_info["sub"]
    username = user_info["name"] or user_info["username"]
    email = user_info["email"]

    # 生成唯一的 user_id
    existing_user_ids = await user_repo.get_all_user_ids()
    base_username = user_info["username"]
    user_id = f"oidc:{sub}"

    # 如果 oidc:{sub} 已存在，添加随机后缀
    if user_id in existing_user_ids:
        import uuid
        user_id = f"oidc:{sub}:{uuid.uuid4().hex[:8]}"

    # 生成随机密码（OIDC 用户不需要密码登录）
    import secrets
    random_password = secrets.token_urlsafe(32)
    password_hash = AuthUtils.hash_password(random_password)

    # 创建用户
    new_user = await user_repo.create({
        "username": username,
        "user_id": user_id,
        "phone_number": None,  # OIDC 用户没有手机号
        "avatar": None,
        "password_hash": password_hash,
        "role": oidc_config.default_role,
        "department_id": department_id,
        "last_login": utc_now_naive(),
    })

    logger.info(f"Created OIDC user: {username} ({user_id})")
    return new_user


async def update_oidc_user_login(db, user: User) -> None:
    """更新 OIDC 用户登录时间"""
    user.last_login = utc_now_naive()
    await db.commit()


def generate_callback_html(token_data: dict, redirect_path: str = "/") -> str:
    """生成 OIDC 回调 HTML 页面

    此页面自动将 token 存储到 localStorage 并重定向到前端
    """
    import json

    # 构建前端回调 URL
    frontend_callback_url = "/auth/oidc/callback"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录处理中...</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            text-align: center;
            color: white;
            padding: 40px;
        }}
        .spinner {{
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        h1 {{
            font-size: 24px;
            font-weight: 500;
            margin-bottom: 10px;
        }}
        p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .error {{
            background: rgba(255, 255, 255, 0.95);
            color: #333;
            padding: 30px;
            border-radius: 12px;
            max-width: 400px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        }}
        .error h2 {{
            color: #e74c3c;
            margin-bottom: 10px;
        }}
        .error p {{
            color: #666;
            margin-bottom: 20px;
        }}
        .error button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }}
        .error button:hover {{
            background: #5a6fd6;
        }}
    </style>
</head>
<body>
    <div class="container" id="container">
        <div class="spinner"></div>
        <h1>登录成功</h1>
        <p>正在跳转，请稍候...</p>
    </div>

    <script>
        (function() {{
            try {{
                // Token 数据
                const tokenData = {json.dumps(token_data, ensure_ascii=False)};

                // 存储 token 到 localStorage
                localStorage.setItem('user_token', tokenData.access_token);

                // 构建前端回调 URL，传递必要的数据
                const params = new URLSearchParams({{
                    token: tokenData.access_token,
                    user_id: String(tokenData.user_id),
                    username: tokenData.username,
                    user_id_login: tokenData.user_id_login,
                    role: tokenData.role,
                }});

                if (tokenData.phone_number) {{
                    params.set('phone_number', tokenData.phone_number);
                }}
                if (tokenData.avatar) {{
                    params.set('avatar', tokenData.avatar);
                }}
                if (tokenData.department_id) {{
                    params.set('department_id', String(tokenData.department_id));
                }}
                if (tokenData.department_name) {{
                    params.set('department_name', tokenData.department_name);
                }}

                // 重定向到前端回调页面
                const redirectUrl = '{frontend_callback_url}?' + params.toString();
                window.location.href = redirectUrl;

            }} catch (error) {{
                console.error('OIDC callback error:', error);
                document.getElementById('container').innerHTML = `
                    <div class="error">
                        <h2>登录处理失败</h2>
                        <p>无法完成登录，请返回登录页重试</p>
                        <button onclick="window.location.href='/login'">返回登录页</button>
                    </div>
                `;
            }}
        }})();
    </script>
</body>
</html>"""
    return html_content


def generate_error_html(error_message: str) -> str:
    """生成错误页面 HTML"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录失败</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .error-container {{
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 16px;
            text-align: center;
            max-width: 400px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        }}
        .error-icon {{
            width: 60px;
            height: 60px;
            background: #e74c3c;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            color: white;
            font-size: 30px;
        }}
        h1 {{
            color: #333;
            font-size: 22px;
            margin-bottom: 10px;
        }}
        p {{
            color: #666;
            font-size: 14px;
            margin-bottom: 25px;
            line-height: 1.6;
        }}
        button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }}
        button:hover {{
            background: #5a6fd6;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">✕</div>
        <h1>登录失败</h1>
        <p>{error_message}</p>
        <button onclick="window.location.href='/login'">返回登录页</button>
    </div>
</body>
</html>"""


# =============================================================================
# === OIDC 路由处理函数 ===
# =============================================================================

async def get_oidc_config_handler():
    """获取 OIDC 配置（供前端使用）"""
    if not oidc_config.enabled or not oidc_config.is_configured():
        return OIDCConfigResponse(enabled=False)

    login_url = await OIDCUtils.build_authorization_url()
    return OIDCConfigResponse(enabled=True, login_url=login_url)


async def oidc_callback_handler(request: Request, code: str, state: str, db):
    """处理 OIDC 回调 - 返回 HTML 页面而不是 JSON"""
    from fastapi import HTTPException, status

    # 验证 state
    state_data = OIDCUtils.verify_state(state)
    if not state_data:
        return HTMLResponse(
            content=generate_error_html("登录会话已过期，请返回登录页重试"),
            status_code=400
        )

    # 用授权码交换令牌
    token_response = await OIDCUtils.exchange_code_for_token(code)
    if not token_response:
        return HTMLResponse(
            content=generate_error_html("无法获取访问令牌，请返回登录页重试"),
            status_code=400
        )

    access_token = token_response.get("access_token")
    if not access_token:
        return HTMLResponse(
            content=generate_error_html("无法获取访问令牌，请返回登录页重试"),
            status_code=400
        )

    # 获取用户信息
    userinfo = await OIDCUtils.get_userinfo(access_token)
    if not userinfo:
        return HTMLResponse(
            content=generate_error_html("无法获取用户信息，请返回登录页重试"),
            status_code=400
        )

    # 提取用户信息
    extracted_info = OIDCUtils.extract_user_info(userinfo)
    sub = extracted_info["sub"]

    if not sub:
        return HTMLResponse(
            content=generate_error_html("无法获取用户标识，请返回登录页重试"),
            status_code=400
        )

    # 查找或创建用户
    user = await find_user_by_oidc_sub(db, sub)

    if user:
        # 更新登录时间
        await update_oidc_user_login(db, user)
        logger.info(f"OIDC user logged in: {user.username}")
    elif oidc_config.auto_create_user:
        # 获取或创建 OIDC 部门
        dept = await get_or_create_oidc_department(db)
        department_id = dept.id if dept else None

        # 创建新用户
        user = await create_oidc_user(db, extracted_info, department_id)
    else:
        return HTMLResponse(
            content=generate_error_html("用户未注册，请联系管理员开通账号"),
            status_code=403
        )

    # 检查用户是否被删除
    if user.is_deleted:
        return HTMLResponse(
            content=generate_error_html("该账户已注销"),
            status_code=403
        )

    # 生成访问令牌
    token_data = {"sub": str(user.id)}
    jwt_token = AuthUtils.create_access_token(token_data)

    # 记录登录操作
    await log_operation(db, user.id, "OIDC 登录")

    # 获取部门名称
    department_name = None
    if user.department_id:
        result = await db.execute(select(Department.name).filter(Department.id == user.department_id))
        department_name = result.scalar_one_or_none()

    # 构建响应数据
    response_data = {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "user_id_login": user.user_id,
        "phone_number": user.phone_number,
        "avatar": user.avatar,
        "role": user.role,
        "department_id": user.department_id,
        "department_name": department_name,
    }

    # 获取重定向路径
    redirect_path = state_data.get("redirect_path", "/")

    # 返回 HTML 页面，自动处理登录并重定向
    return HTMLResponse(
        content=generate_callback_html(response_data, redirect_path),
        status_code=200
    )


async def oidc_login_url_handler(redirect_path: str = "/"):
    """获取 OIDC 登录 URL"""
    from fastapi import HTTPException, status

    if not oidc_config.enabled or not oidc_config.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC is not enabled or not configured"
        )

    login_url = await OIDCUtils.build_authorization_url(redirect_path)
    if not login_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build authorization URL"
        )

    return {"login_url": login_url}
