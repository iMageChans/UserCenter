import polib
import os

def generate_mo_file(po_path, mo_path):
    if os.path.exists(po_path):
        po = polib.pofile(po_path)
        po.save_as_mofile(mo_path)
        print(f"Generated {mo_path} from {po_path}")
    else:
        print(f"Warning: {po_path} does not exist")

# 确保目录存在
for lang in ['en', 'ja', 'ko']:
    os.makedirs(f'locale/{lang}/LC_MESSAGES', exist_ok=True)

# 生成 .mo 文件
generate_mo_file('locale/en/LC_MESSAGES/django.po', 'locale/en/LC_MESSAGES/django.mo')
generate_mo_file('locale/ja/LC_MESSAGES/django.po', 'locale/ja/LC_MESSAGES/django.mo')
generate_mo_file('locale/ko/LC_MESSAGES/django.po', 'locale/ko/LC_MESSAGES/django.mo') 