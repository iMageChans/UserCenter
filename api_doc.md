# UserCenter API 文档

## 基础信息

- 基础URL: `/api/`
- 认证方式: Token认证（在请求头中添加 `Authorization: <your_token>`）
- 响应格式: JSON
- 支持语言: 中文(zh-hans)、英文(en)、西班牙语(es)、葡萄牙语(pt)、法语(fr)、日语(ja)、韩语(ko)

## 1. 认证相关

### 1.1 获取认证令牌

通过用户名和密码获取认证令牌。

- **URL**: `/api/auth/token/`
- **方法**: `POST`
- **认证**: 不需要
- **权限**: 任何人

**请求参数**:

- `username`: 用户名或邮箱
- `password`: 密码

**响应参数**:

```json
{
  "code": 200,
  "msg": "成功",
  "data": {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
  }
}
```

### 1.2 第三方登录

使用第三方OAuth服务进行登录或注册。

- **URL**: `/api/auth/social-login/`
- **方法**: `POST`
- **认证**: 不需要
- **权限**: 任何人

**请求参数**:

```json
{
  "provider": "wechat",  // 提供商: wechat, apple, google, github 等
  "code": "授权码",
  "redirect_uri": "https://your-app.example.com/callback",  // 可选，某些提供商需要
  "app_id": "your_app_id"  // 可选，用于区分不同应用的配置，默认为 "default"
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "user": {
      "id": 1,
      "username": "user1",
      "email": "user1@example.com",
      "nickname": "用户1",
      "avatar": "https://example.com/avatar.jpg",
      "phone": "13800138000",
      "is_verified": true,
      "language": "zh-hans",
      "timezone": "Asia/Shanghai",
      "date_joined": 1582790006000,
      "last_login": 1582790006000
    },
    "is_new_user": false  // 是否新注册的用户
  }
}
```

**支持的提供商**:

- `wechat`: 微信
- `apple`: 苹果
- `google`: 谷歌
- `github`: GitHub
- `qq`: QQ
- `weibo`: 微博
- `alipay`: 支付宝
- `dingtalk`: 钉钉

**多应用支持**:

UserCenter 支持为不同的应用配置不同的第三方登录参数。通过在请求中提供 `app_id` 参数，系统会使用对应应用的配置进行第三方登录。如果未提供 `app_id` 或找不到对应配置，系统会尝试使用 `default` 应用的配置。

### 1.3 用户注册

注册新用户。

- **URL**: `/api/auth/register/`
- **方法**: `POST`
- **认证**: 不需要
- **权限**: 任何人

**请求参数**:

```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "password123",
  "confirm_password": "password123",
  "nickname": "用户1",
  "phone": "13800138000"
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "注册成功",
  "data": {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "user": {
      "id": 1,
      "username": "user1",
      "email": "user1@example.com",
      "nickname": "用户1",
      "avatar": "",
      "phone": "13800138000",
      "is_verified": false,
      "language": "zh-hans",
      "timezone": "Asia/Shanghai",
      "date_joined": 1582790006000,
      "last_login": 1582790006000
    }
  }
}
```

## 2. 用户相关

### 2.1 获取当前用户信息

获取当前登录用户的详细信息。

- **URL**: `/api/users/me/`
- **方法**: `GET`
- **认证**: 需要
- **权限**: 已认证用户

**响应参数**:

```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "id": 1,
    "username": "user1",
    "email": "user1@example.com",
    "nickname": "用户1",
    "avatar": "https://example.com/avatar.jpg",
    "phone": "13800138000",
    "is_verified": true,
    "language": "zh-hans",
    "timezone": "Asia/Shanghai",
    "date_joined": 1582790006000,
    "last_login": 1582790006000
  }
}
```

### 2.2 修改密码

修改当前用户的密码。

- **URL**: `/api/users/change_password/`
- **方法**: `POST`
- **认证**: 需要
- **权限**: 已认证用户

**请求参数**:

```json
{
  "old_password": "old_password",
  "new_password": "new_password"
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "密码修改成功",
  "data": {}
}
```

### 2.3 获取用户关联的第三方账号

获取当前用户关联的所有第三方账号。

- **URL**: `/api/users/oauth_accounts/`
- **方法**: `GET`
- **认证**: 需要
- **权限**: 已认证用户

**响应参数**:

```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "id": 1,
      "provider": {
        "id": 1,
        "name": "wechat",
        "is_active": true
      },
      "provider_user_id": "openid123",
      "created_at": 1582790006000
    },
    {
      "id": 2,
      "provider": {
        "id": 2,
        "name": "apple",
        "is_active": true
      },
      "provider_user_id": "apple_user_id",
      "created_at": 1582790006000
    }
  ]
}
```

## 3. OAuth提供商相关

### 3.1 获取可用的OAuth提供商列表

获取所有可用的OAuth提供商。

- **URL**: `/api/oauth-providers/`
- **方法**: `GET`
- **认证**: 不需要
- **权限**: 任何人

**响应参数**:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "wechat",
      "is_active": true
    },
    {
      "id": 2,
      "name": "apple",
      "is_active": true
    }
  ]
}
```

## 4. 优惠码相关

### 4.1 获取优惠码列表（仅限管理员）

获取系统中的优惠码列表。

- **URL**: `/api/magics/codes/`
- **方法**: `GET`
- **认证**: 需要
- **权限**: 仅限管理员
- **查询参数**:
  - `app_id`: 筛选特定应用的优惠码
  - `status`: 筛选特定状态的优惠码（active, expired, used_up, disabled）

**响应参数**:

```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "id": 1,
      "code": "PREMIUM2023",
      "app_id": "default",
      "days": 30,
      "max_uses": 100,
      "used_count": 5,
      "status": "active",
      "expires_at": 1613412406000,
      "created_at": 1582790006000,
      "updated_at": 1582790006000
    },
    {
      "id": 2,
      "code": "WELCOME50",
      "app_id": "mobile",
      "days": 7,
      "max_uses": 1,
      "used_count": 0,
      "status": "active",
      "expires_at": 1613412406000,
      "created_at": 1582790006000,
      "updated_at": 1582790006000
    }
  ]
}
```

### 4.2 创建优惠码（仅限管理员）

创建新的优惠码。

- **URL**: `/api/magics/codes/`
- **方法**: `POST`
- **认证**: 需要
- **权限**: 仅限管理员

**请求参数**:

```json
{
  "app_id": "default",
  "days": 30,
  "max_uses": 100,
  "status": "active",
  "expires_at": 1613412406000
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "创建成功",
  "data": {
    "id": 3,
    "code": "AUTO12345",
    "app_id": "default",
    "days": 30,
    "max_uses": 100,
    "used_count": 0,
    "status": "active",
    "expires_at": 1613412406000,
    "created_at": 1582790006000,
    "updated_at": 1582790006000
  }
}
```

### 4.3 生成单个优惠码（仅限管理员）

生成单个随机优惠码。

- **URL**: `/api/magics/codes/generate/`
- **方法**: `POST`
- **认证**: 需要
- **权限**: 仅限管理员

**请求参数**:

```json
{
  "app_id": "default",
  "days": 30,
  "max_uses": 1,
  "prefix": "PROMO",
  "expires_days": 90
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "优惠码生成成功",
  "data": {
    "id": 4,
    "code": "PROMO12345",
    "app_id": "default",
    "days": 30,
    "max_uses": 1,
    "used_count": 0,
    "status": "active",
    "expires_at": 1613412406000,
    "created_at": 1582790006000,
    "updated_at": 1582790006000
  }
}
```

### 4.4 批量生成优惠码（仅限管理员）

批量生成随机优惠码。

- **URL**: `/api/magics/codes/batch_generate/`
- **方法**: `POST`
- **认证**: 需要
- **权限**: 仅限管理员

**请求参数**:

```json
{
  "app_id": "default",
  "days": 30,
  "max_uses": 1,
  "count": 10,
  "prefix": "BATCH",
  "expires_days": 90
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "批量生成优惠码成功",
  "data": [
    {
      "id": 5,
      "code": "BATCH1234",
      "app_id": "default",
      "days": 30,
      "max_uses": 1,
      "used_count": 0,
      "status": "active",
      "expires_at": 1613412406000,
      "created_at": 1582790006000,
      "updated_at": 1582790006000
    },
    // ... 更多优惠码
  ]
}
```

### 4.5 禁用优惠码（仅限管理员）

禁用指定的优惠码。

- **URL**: `/api/magics/codes/{code_id}/disable/`
- **方法**: `POST`
- **认证**: 需要
- **权限**: 仅限管理员

**响应参数**:

```json
{
  "code": 200,
  "msg": "优惠码已禁用",
  "data": {
    "id": 1,
    "code": "PREMIUM2023",
    "app_id": "default",
    "days": 30,
    "max_uses": 100,
    "used_count": 5,
    "status": "disabled",
    "expires_at": 1613412406000,
    "created_at": 1582790006000,
    "updated_at": 1582790006000
  }
}
```

### 4.6 获取优惠码使用记录（仅限管理员）

获取指定优惠码的使用记录。

- **URL**: `/api/magics/codes/{code_id}/usage_records/`
- **方法**: `GET`
- **认证**: 需要
- **权限**: 仅限管理员

**响应参数**:

```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {
      "id": 1,
      "code": "PREMIUM2023",
      "username": "user1",
      "used_at": 1582790006000
    },
    {
      "id": 2,
      "code": "PREMIUM2023",
      "username": "user2",
      "used_at": 1582876406000
    }
  ]
}
```

### 4.7 兑换优惠码（用户接口）

用户兑换优惠码获取会员权益。

- **URL**: `/api/magics/redeem/`
- **方法**: `POST`
- **认证**: 需要
- **权限**: 认证用户

**请求参数**:

```json
{
  "code": "PREMIUM2023",
  "app_id": "default"
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "优惠码兑换成功，已获得 30 天会员权益",
  "data": {
    "days_added": 30,
    "premium_expiry": 1613412406000
  }
}
```

**可能的错误响应**:

- 优惠码不存在:
```json
{
  "code": 404,
  "msg": "优惠码不存在",
  "data": null
}
```

- 优惠码已使用:
```json
{
  "code": 400,
  "msg": "您已经使用过此优惠码",
  "data": null
}
```

- 优惠码无效或已过期:
```json
{
  "code": 400,
  "msg": "优惠码无效或已过期",
  "data": null
}
```

## 5. 国际化支持

所有API响应都支持国际化，可以通过以下方式指定语言：

1. 在请求头中设置 `Accept-Language`：
   ```
   Accept-Language: es
   ```

2. 在URL中添加语言参数：
   ```
   ?lang=fr
   ```

3. 通过用户设置（需要登录）：
   ```
   POST /api/set-language/
   {"language": "ja"}
   ```

支持的语言代码：

- `zh-hans`: 简体中文（默认）
- `en`: 英文
- `es`: 西班牙语
- `pt`: 葡萄牙语
- `fr`: 法语
- `ja`: 日语
- `ko`: 韩语

### 5.1 获取可用语言列表

- **URL**: `/api/languages/`
- **方法**: `GET`
- **认证**: 不需要
- **权限**: 任何人

**响应参数**:

```json
{
  "code": 200,
  "msg": "获取成功",
  "data": [
    {"code": "zh-hans", "name": "简体中文"},
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Español"},
    {"code": "pt", "name": "Português"},
    {"code": "fr", "name": "Français"},
    {"code": "ja", "name": "日本語"},
    {"code": "ko", "name": "한국어"}
  ]
}
```

### 5.2 设置用户偏好语言

- **URL**: `/api/set-language/`
- **方法**: `POST`
- **认证**: 需要
- **权限**: 认证用户

**请求参数**:

```json
{
  "language": "en"  // 语言代码
}
```

**响应参数**:

```json
{
  "code": 200,
  "msg": "语言设置成功",
  "data": {
    "language": "en"
  }
}
```

## 6. 速率限制

- 匿名用户：每分钟60次请求
- 认证用户：每分钟300次请求
- 登录尝试：每IP每小时10次
- 密码修改：每用户每天5次

## 7. 安全建议

1. 所有API请求应使用HTTPS
2. 存储令牌时应使用安全存储（如HttpOnly Cookie）
3. 定期轮换令牌
4. 敏感操作应要求重新验证
5. 遵循最小权限原则

**时间格式**:

所有时间字段都使用时间戳（毫秒）格式，例如：

```json
{
  "date_joined": 1582790006000,  // 2020-02-27 09:13:26 UTC
  "last_login": 1582790006000
}
```

ba58c96081cf175352f084c4d76b9252213c36ea

