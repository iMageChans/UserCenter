# 使用官方 Python 轻量级镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    DJANGO_SETTINGS_MODULE=UserCenter.settings \
    DJANGO_ENV=development \
    PYTHONPATH=/app

# 替换为阿里云的 Debian 镜像源
# 替换为阿里云的 Debian 镜像源
RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bullseye-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-backports main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bullseye-security main" >> /etc/apt/sources.list

# 删除额外的源文件
RUN rm -rf /etc/apt/sources.list.d/*

# 禁用默认源
RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo 'Acquire::Check-Date "false";' >> /etc/apt/apt.conf.d/99no-check-valid-until

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目依赖文件
COPY requirements/dev.txt dev.txt
COPY requirements/base.txt base.txt

# 更换 pip 源为阿里云镜像并安装项目依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r dev.txt

# 显式安装 gunicorn
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ gunicorn==21.2.0

# 复制项目文件
COPY . .

RUN mkdir -p /app/templates/admin/magics/magiccode/

# 确保 settings 目录被识别为 Python 包
RUN touch UserCenter/settings/__init__.py

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "UserCenter.wsgi:application"]