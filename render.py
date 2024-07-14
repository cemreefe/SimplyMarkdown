import os
import re
import argparse

from generateSitemap import generate_sitemap
from generateRSS import generate_rss_feed
from helpers import *
from markdownTags import get_first_title
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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

def replace_relative_src_links(html_content, reldir, root_url):
    # Ensure root_url does not end with a slash
    root_url = root_url.rstrip('/')
    reldir = reldir.lstrip('/').rstrip('/')
    
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all elements with a src attribute
    for tag in soup.find_all(src=True):
        src = tag['src']
        
        # Check if the src is a relative path (does not start with http://, https://, or /)
        if not src.startswith(('http://', 'https://', '/')):
            # Construct the new src value
            new_src = urljoin(f'{root_url}/{reldir}/', src)
            tag['src'] = new_src
        elif src.startswith('/'):
            # Handle absolute paths relative to the root URL
            src = src.lstrip('/')
            new_src = urljoin(root_url, src)
            tag['src'] = new_src
    
    # Return the modified HTML content as a string
    return str(soup)

def process_markdown_file(input_path, file_path, output_file_, module_dict, root, urlroot, favicon, website_title, template_path, output_path):
    """Processes a Markdown file, converts it to HTML, and fills in the template."""
    content = read_file_content(file_path)
    title = get_first_title(content)
    
    # Change the file extension to '.html'
    output_file = os.path.splitext(output_file_)[0].replace(', ', '-').replace(' ', '-') + '.html'
    output_file_relpath = os.path.relpath(output_file, output_path)
    output_dir_relpath = os.path.dirname(output_file_relpath)
    
    # Replace module tags in the content
    content = re.sub('\n! include (.+)', lambda match: module_dict.get(match.group(1), ""), content, flags=re.I)
    content, meta = convert_to_html(content, os.path.dirname(file_path))
    content = replace_relative_src_links(content, output_dir_relpath, urlroot)

    meta_img_override = meta.get('image', [None])[0]
    meta_title = meta.get('title', [title])[0]
    meta_description = meta.get('description', [extract_first_paragraph(content)])[0]
    meta_canonical_uri = meta.get('canonical_uri', [None])[0]
    meta_date = meta.get('date', [None])[0]

    meta_tags = get_meta_tags(meta_img_override, meta_title, meta_description, meta_date, urlroot, root, input_path, output_file_relpath, meta_canonical_uri)

    meta_lang = meta.get('language', ['en'])[0]

    category_tags = meta.get('tags', [])

    meta_title = f"{meta_title} - {website_title}"

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

    with open(output_file, 'w') as f:
        f.write(filled_template)


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

            if file.lower().endswith(('.md')) or (file.lower().endswith(('.html')) and '<convertsm>' in open(file_path).read()) :
                # If the file is markdown, convert to HTML and replace module tags
                process_markdown_file(input_path, file_path, output_file, module_dict, root, urlroot, favicon, website_title, template_path, output_path)

            else:
                # For non-md and non-html files, copy them as is to the output directory
                shutil.copy2(file_path, output_file)

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
    parser.add_argument('--rss-whitelist', default='*', help='Comma-separated list of URI patterns to include in the feed (supports wildcards).')
    parser.add_argument('--rss-description', default='This is an RSS feed of my website.', help='Description of the RSS feed.')
    args = parser.parse_args()

    process_directory(args.input, args.output, args.css, args.template, args.favicon, args.root, args.title)
    generate_sitemap(args.output, args.root)
    generate_rss_feed(args.output, args.root, args.rss_whitelist, args.title, args.rss_description)
