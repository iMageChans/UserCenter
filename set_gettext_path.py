import os

# 假设 gettext 工具安装在以下位置（根据您的实际安装路径调整）
gettext_path = r"C:\Program Files\gettext-iconv\bin"

# 将路径添加到环境变量
if gettext_path not in os.environ['PATH']:
    os.environ['PATH'] = gettext_path + os.pathsep + os.environ['PATH']
    print(f"Added {gettext_path} to PATH")
else:
    print(f"{gettext_path} already in PATH")

# 验证 msgfmt 是否可用
import subprocess
try:
    result = subprocess.run(['msgfmt', '--version'], capture_output=True, text=True)
    print("msgfmt version:", result.stdout)
except Exception as e:
    print("Error running msgfmt:", e)

# 尝试编译翻译文件
try:
    from django.core.management import call_command
    call_command('compilemessages')
    print("Successfully compiled messages")
except Exception as e:
    print("Error compiling messages:", e) 