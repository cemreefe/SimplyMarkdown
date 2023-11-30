import os
import re
import argparse

from generateSitemap import generate_sitemap
from helpers import *
from markdownTags import get_first_title

def find_modules(directory):
    """Finds and returns a dictionary containing module filenames and their content."""
    module_dict = {}
    modules_dir = os.path.join(directory, 'modules')
    
    if not os.path.exists(modules_dir):
        return module_dict
    
    for root, _, files in os.walk(modules_dir):
        for file in files:
            file_path = os.path.join(root, file)
            module_dict[get_filename_without_extension(file)], _ = convert_to_html(read_file_content(file_path), os.path.dirname(file_path))   
    return module_dict

def process_markdown_file(input_path, file_path, output_file, module_dict, root, urlroot, favicon, website_title, template_path):
    """Processes a Markdown file, converts it to HTML, and fills in the template."""
    content = read_file_content(file_path)
    title = get_first_title(content)
    
    # Replace module tags in the content
    content = re.sub('\n! include (.+)', lambda match: module_dict.get(match.group(1), ""), content, flags=re.I)
    content, meta = convert_to_html(content, os.path.dirname(file_path))

    meta_img_override = meta.get('image', [None])[0]
    meta_title = meta.get('title', [title])[0]
    meta_description = meta.get('description', [extract_first_paragraph(content)])[0]

    meta_tags = get_meta_tags(meta_img_override, meta_title, meta_description, urlroot, root, input_path)

    meta_lang = meta.get('language', ['en'])[0]

    category_tags = meta.get('tags', [])

    # Change the file extension to '.html'
    output_file = os.path.splitext(output_file)[0].replace(', ', '-').replace(' ', '-') + '.html'

    # Fill in the template with the context information
    context = {
        'lang': meta_lang,
        'root': urlroot,
        'favicon_path': get_dutluk_emoji_href(favicon),
        'title': meta_title,
        'modules': module_dict,
        'content': content,
        'meta_tags': meta_tags,
        'category_tags': category_tags
    }
    filled_template = fill_template({'context': context}, template_path)

    with open(output_file, 'w') as output_file:
        output_file.write(filled_template)


def process_directory(input_path, output_path, css, template_path, favicon, urlroot, website_title):
    """Processes the input directory and saves the files in the output directory."""
    # Copy the CSS file to the output directory
    copy_css_file(css, output_path)

    module_dict = find_modules(input_path)

    for root, dirs, files in os.walk(input_path):
        for dir_name in dirs:
            input_dir = os.path.join(root, dir_name)
            output_dir = input_dir.replace(input_path, output_path)
            os.makedirs(output_dir, exist_ok=True)

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = file_path.replace(input_path, '').lstrip('/\\')
            output_file = os.path.join(output_path, relative_path)

            if relative_path.startswith('modules/') or relative_path.startswith('_'):
                # For files in 'modules', already handled in find_modules()
                continue

            if file.lower().endswith(('.md')) or (file.lower().endswith(('.html')) and '<convertsm>' in file.read()) :
                # For non-md and non-html files, copy them as is to the output directory
                shutil.copy2(file_path, output_file)

            else:
                # If the file is markdown, convert to HTML and replace module tags
                process_markdown_file(input_path, file_path, output_file, module_dict, root, urlroot, favicon, website_title, template_path)

if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description="Process files in input directory.")
    parser.add_argument('-i', '--input', help="Input directory path", required=True)
    parser.add_argument('-o', '--output', help="Output directory path", required=True)
    parser.add_argument('--css', help="CSS to include", required=False, default='themes/basic.css')
    parser.add_argument('--template', help="Path to the HTML template", required=False, default='templates/base.html')
    parser.add_argument('--favicon', help="Favicon emoji", required=False, default='👤')
    parser.add_argument('--root', help="Project url root", required=False, default='')
    parser.add_argument('--title', help="Website title", required=False, default='')
    args = parser.parse_args()

    process_directory(args.input, args.output, args.css, args.template, args.favicon, args.root, args.title)
    generate_sitemap(args.output, args.root)
