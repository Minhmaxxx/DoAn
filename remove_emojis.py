import os
import glob
import re
import emoji

def clean_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove Streamlit icon parameters (e.g., icon="⚠️", page_icon="🥗")
    content = re.sub(r',\s*icon="[^"]+"', '', content)
    content = re.sub(r",\s*icon='[^']+'", '', content)
    content = re.sub(r',\s*page_icon="[^"]+"', '', content)
    content = re.sub(r",\s*page_icon='[^']+'", '', content)

    # 2. Fix the Gemini 1.5 Flash reference
    content = content.replace('Gemini 1.5 Flash', 'Google Gemini')
    content = content.replace('gemini-1.5-flash', 'gemini-pro')
    content = content.replace('Gemini%201.5%20Flash', 'Google%20Gemini')
    content = content.replace('Gemini 1.5', 'Gemini')

    # 3. Strip all remaining emojis
    clean_content = emoji.replace_emoji(content, replace='')

    # 4. Cleanup weird spacing left behind in Markdown
    clean_content = clean_content.replace('#  ', '# ')
    clean_content = clean_content.replace('-  ', '- ')
    clean_content = clean_content.replace('**  ', '** ')
    clean_content = clean_content.replace('  **', ' **')
    clean_content = clean_content.replace('  —', ' —')
    
    if content != clean_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(clean_content)
        print(f"Updated: {file_path}")

files_to_process = []
for ext in ['*.md', '*.py', 'run.bat']:
    files_to_process.extend(glob.glob(f'**/{ext}', recursive=True))

for file in files_to_process:
    if '.venv' in file or 'venv' in file or '__pycache__' in file or 'remove_emojis' in file:
        continue
    clean_file(file)

print("Done cleaning codebase!")
