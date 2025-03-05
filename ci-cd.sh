#!/bin/bash
set -e  # 任何命令失败就退出

# 1. 安装依赖
echo "安装依赖..."
pip install -r requirements/dev.txt

# 2. 运行测试
echo "运行测试..."
python manage.py test user.tests

# 3. 如果测试通过，构建 Docker 镜像
if [ $? -eq 0 ]; then
    echo "测试通过，构建 Docker 镜像..."
    docker-compose build

    # 4. 启动服务
    echo "启动服务..."
    docker-compose up -d
else
    echo "测试失败，中止部署"
    exit 1
fi

echo "部署完成" 



# version: '3.8'
#     services:  web:    
#     image: 'gitlab/gitlab-ce:latest'    
#     restart: always    
#     container_name: gitlab-ce    
#         # hostname: '/git'    
#     environment:      
#         GITLAB_OMNIBUS_CONFIG: 
#         #       external_url '/git'        
#         # Add any other gitlab.rb configuration here, each on its own line    
#     ports:      
#         - '8088:80'      
#         - '8089:443'      
#         - '8090:22'    
#     volumes:      
#         - '$GITLAB_HOME/config:/etc/gitlab'      
#         - '$GITLAB_HOME/logs:/var/log/gitlab'      
#         - '$GITLAB_HOME/data:/var/opt/gitlab'    
#     shm_size: '256m'