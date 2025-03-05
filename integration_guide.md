# UserCenter 集成指南

## 概述

UserCenter 是公司统一的用户认证和授权中心，提供以下功能：

- 用户注册、登录和身份验证
- OAuth2.0 授权
- 第三方社交账号登录（微信、苹果等）
- 用户信息管理
- 多语言支持（中文、英语、日语、韩语）

本指南将帮助您将现有应用与 UserCenter 集成，实现统一的用户管理。

## 集成方式

UserCenter 支持两种主要的集成方式：

1. **OAuth 2.0 集成**：适用于独立部署的应用，通过标准 OAuth 2.0 协议与 UserCenter 交互
2. **API 集成**：通过 REST API 直接与 UserCenter 交互，适用于微服务架构

## 1. OAuth 2.0 集成

### 1.1 注册应用

首先，您需要在 UserCenter 管理后台注册您的应用：

1. 访问 UserCenter 管理后台 (https://usercenter.example.com/admin/)
2. 导航至 "OAuth 应用程序" 部分
3. 点击 "添加应用程序"
4. 填写以下信息：
   - 应用名称：您的应用名称
   - 客户端类型：选择 "机密" 或 "公开"
   - 重定向 URI：授权后重定向的 URI
   - 授权类型：选择支持的授权类型（授权码、隐式、密码、客户端凭证）
5. 保存后，您将获得 `client_id` 和 `client_secret`

### 1.2 实现 OAuth 2.0 授权流程

#### 授权码流程（推荐）

1. **重定向用户到授权页面**

```
https://usercenter.example.com/o/authorize/?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=read write&state=RANDOM_STATE
```

2. **用户授权后，获取授权码**

用户授权后，UserCenter 将重定向到您的 `redirect_uri`，并附加授权码：

```
https://your-app.example.com/callback?code=AUTHORIZATION_CODE&state=RANDOM_STATE
```

3. **使用授权码获取访问令牌**

```http
POST https://usercenter.example.com/o/token/
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=AUTHORIZATION_CODE
&redirect_uri=YOUR_REDIRECT_URI
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
```

响应：

```json
{
  "access_token": "ACCESS_TOKEN",
  "token_type": "Bearer",
  "expires_in": 36000,
  "refresh_token": "REFRESH_TOKEN",
  "scope": "read write"
}
```

4. **使用访问令牌访问 API**

```http
GET https://usercenter.example.com/api/users/me/
Authorization: Bearer ACCESS_TOKEN
```

#### 客户端凭证流程（服务器间通信）

```http
POST https://usercenter.example.com/o/token/
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&scope=read
```

### 1.3 刷新访问令牌

```http
POST https://usercenter.example.com/o/token/
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=REFRESH_TOKEN
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
```

## 2. API 集成

如果您的应用是内部微服务，可以直接使用 API 集成方式。

### 2.1 获取 API 密钥

联系 UserCenter 管理员获取 API 密钥。

### 2.2 用户认证

#### 用户名密码认证

```http
POST https://usercenter.example.com/api/auth/token/
Content-Type: application/json

{
  "username": "user_name",
  "password": "user_password"
}
```

响应：

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

#### 第三方登录

```http
POST https://usercenter.example.com/api/auth/social-login/
Content-Type: application/json

{
  "provider": "wechat",
  "code": "AUTHORIZATION_CODE",
  "redirect_uri": "https://your-app.example.com/callback"
}
```

响应：

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 1,
    "username": "user123",
    "nickname": "用户昵称",
    "avatar": "https://example.com/avatar.jpg",
    "email": "user@example.com",
    "phone": "13800138000",
    "is_verified": true
  }
}
```

### 2.3 用户信息管理

#### 获取当前用户信息

```http
GET https://usercenter.example.com/api/users/me/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

#### 修改用户信息

```http
PATCH https://usercenter.example.com/api/users/1/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "nickname": "新昵称",
  "avatar": "https://example.com/new-avatar.jpg"
}
```

#### 用户注册

```http
POST https://usercenter.example.com/api/auth/register/
Content-Type: application/json

{
  "username": "new_user",
  "email": "user@example.com",
  "password": "secure_password",
  "confirm_password": "secure_password",
  "nickname": "用户昵称",
  "phone": "13800138000"
}
```

注册成功后，将直接返回认证令牌和用户信息：

```json
{
  "detail": "注册成功",
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 1,
    "username": "new_user",
    "nickname": "用户昵称",
    "email": "user@example.com",
    "is_verified": true
  }
}
```

## 3. 单点登录 (SSO) 实现

### 3.1 前端实现

使用共享 Cookie 域实现单点登录：

1. UserCenter 设置 Cookie 在顶级域名（如 `.example.com`）
2. 所有子域名应用（如 `app1.example.com`, `app2.example.com`）可以访问该 Cookie

前端代码示例：

```javascript
// 检查用户是否已登录
async function checkLoginStatus() {
  try {
    const response = await fetch('https://usercenter.example.com/api/users/me/', {
      credentials: 'include' // 包含 cookies
    });
    
    if (response.ok) {
      const userData = await response.json();
      // 用户已登录，更新UI
      showLoggedInUI(userData);
    } else {
      // 用户未登录，显示登录按钮
      showLoginButton();
    }
  } catch (error) {
    console.error('检查登录状态失败:', error);
    showLoginButton();
  }
}

// 重定向到登录页面
function redirectToLogin() {
  const currentUrl = encodeURIComponent(window.location.href);
  window.location.href = `https://usercenter.example.com/login?next=${currentUrl}`;
}
```

### 3.2 后端实现

后端服务可以通过验证令牌来确认用户身份：

```python
import requests

def verify_user_token(token):
    response = requests.get(
        'https://usercenter.example.com/api/users/me/',
        headers={'Authorization': f'Token {token}'}
    )
    
    if response.status_code == 200:
        return response.json()  # 返回用户信息
    return None  # 令牌无效
```

## 4. 最佳实践

### 4.1 安全建议

1. 使用 HTTPS 进行所有通信
2. 存储令牌时使用安全存储（如 HttpOnly Cookie）
3. 实现 CSRF 保护
4. 定期轮换令牌
5. 敏感操作应要求重新验证
6. 遵循最小权限原则

### 4.2 性能优化

1. 缓存用户信息
2. 使用长期令牌减少认证请求
3. 实现令牌预刷新，避免令牌过期导致的服务中断

### 4.3 错误处理

1. 实现优雅的错误处理和重试机制
2. 当认证失败时，提供清晰的错误消息
3. 监控认证失败率，及时发现问题

## 5. 常见问题

### 5.1 令牌过期

问题：访问令牌已过期，API 请求返回 401 错误。

解决方案：使用刷新令牌获取新的访问令牌。如果刷新令牌也已过期，则需要用户重新登录。

### 5.2 跨域问题

问题：浏览器阻止跨域请求。

解决方案：确保 UserCenter 服务器配置了正确的 CORS 头，允许您的应用域名。

### 5.3 Cookie 不共享

问题：单点登录不工作，Cookie 不在应用间共享。

解决方案：确保所有应用使用相同的顶级域名，并且 Cookie 设置了正确的域和路径。

## 6. 联系支持

如果您在集成过程中遇到任何问题，请联系 UserCenter 团队：

- 邮箱：usercenter-support@example.com
- 内部工单系统：[提交工单](https://support.example.com)

## 7. 更新日志

- **2024-02-27**: 初始版本发布
- **2024-03-01**: 添加第三方登录文档
- **2024-03-15**: 添加单点登录实现指南 